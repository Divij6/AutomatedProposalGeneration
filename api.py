from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
import uuid
import tempfile
import logging
from typing import Optional
from pathlib import Path
from fastapi import UploadFile, File, Form

from pipeline_one.parsing.pipeline import run_parsing_pipeline
from pipeline_one.chunking.pipeline import run_chunking_pipeline
from pipeline_one.embedding.pipeline import run_embedding_pipeline
from pipeline_one.proposal.llm_proposal_detector import detect_proposal_formats_with_llm
from pipeline_one.proposal.extractor import extract_proposal_pdf
from pipeline_one.proposal.json_builder import build_proposal_json
from pipeline_one.proposal.llm_format_validator import validate_and_normalise_proposal_json
from pipeline_one.utils.supabase_client import supabase, upload_file_to_supabase

from agents.graph import build_graph

from docx import Document
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import bcrypt

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def convert_docx_to_pdf(docx_path: str) -> str:
    """Minimal DOCX→PDF via reportlab (text only — use only for knowledge base, NOT for templates)."""
    pdf_path = docx_path.replace(".docx", ".pdf")
    doc = Document(docx_path)
    styles = getSampleStyleSheet()
    elements = [Paragraph(p.text, styles["Normal"]) for p in doc.paragraphs if p.text.strip()]
    pdf = SimpleDocTemplate(pdf_path, pagesize=letter)
    pdf.build(elements)
    return pdf_path


def build_proposal_json_from_docx(docx_path: str) -> dict:
    """
    Parse a DOCX template directly (preserving tables) into proposal_json format.

    proposal_json structure:
    {
        "sections": [
            {
                "title": "Section Heading",
                "paragraphs": ["text..."],
                "tables": [
                    {
                        "rows": [
                            ["Sr No", "Specification Required", "Specification Offered"],
                            ["1",     "Power rating",           ""],
                            ...
                        ]
                    }
                ]
            }
        ]
    }
    """
    doc = Document(docx_path)
    sections = []
    current_section = {"title": "Main", "paragraphs": [], "tables": []}

    for block in doc.element.body:
        tag = block.tag.split("}")[-1]  # strip namespace

        if tag == "p":
            # It's a paragraph — check if it's a heading
            para = None
            for p in doc.paragraphs:
                if p._element is block:
                    para = p
                    break
            if para is None:
                continue

            style_name = para.style.name.lower() if para.style else ""
            text = para.text.strip()

            if not text:
                continue

            if "heading" in style_name:
                # Start a new section
                if current_section["paragraphs"] or current_section["tables"]:
                    sections.append(current_section)
                current_section = {"title": text, "paragraphs": [], "tables": []}
            else:
                current_section["paragraphs"].append(text)

        elif tag == "tbl":
            # It's a table — extract all rows
            tbl = None
            for t in doc.tables:
                if t._element is block:
                    tbl = t
                    break
            if tbl is None:
                continue

            rows = []
            for row in tbl.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                rows.append(row_data)

            if rows:
                current_section["tables"].append({"rows": rows})

    # Don't forget last section
    if current_section["paragraphs"] or current_section["tables"]:
        sections.append(current_section)

    return {"sections": sections}


def _filename_from_storage_path(path: Optional[str]) -> str:
    if not path:
        return ""
    return os.path.basename(str(path))


def _delete_company_knowledge_vectors(company_id: str) -> None:
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_KEY,
        timeout=60,
    )
    client.delete(
        collection_name="company_knowledge",
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="company_id",
                        match=MatchValue(value=company_id),
                    ),
                ],
            ),
        ),
    )


def _embed_company_knowledge(kb_path: str, company_id: str, replace_existing: bool = False) -> dict:
    if replace_existing:
        try:
            _delete_company_knowledge_vectors(company_id)
        except Exception as e:
            logger.warning("Could not delete existing company knowledge vectors for %s: %s", company_id, e)

    kb_bytes = supabase.storage.from_("company-documents").download(kb_path)
    file_ext = kb_path.split(".")[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
        tmp.write(kb_bytes)
        temp_kb_path = tmp.name

    # Convert DOCX to PDF only for the knowledge base (parser expects PDF).
    if temp_kb_path.endswith(".docx"):
        temp_kb_path = convert_docx_to_pdf(temp_kb_path)

    parsed_doc = run_parsing_pipeline(pdf_path=temp_kb_path)
    chunks = run_chunking_pipeline(parsed_doc)
    for chunk in chunks:
        chunk.metadata["company_id"] = company_id

    embedding_result = run_embedding_pipeline(
        chunks=chunks,
        doc_id=company_id,
        cohere_key=COHERE_KEY,
        qdrant_url=QDRANT_URL,
        qdrant_key=QDRANT_KEY,
        collection_name="company_knowledge",
    )
    logger.info("Company knowledge embedded: %s chunks", len(chunks))
    return embedding_result


# ── App setup ──────────────────────────────────────────────────────────────────

UPLOAD_DIR = Path("uploaded_pdfs")
UPLOAD_DIR.mkdir(exist_ok=True)

COHERE_KEY = os.getenv("COHERE_KEY")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_KEY = os.getenv("QDRANT_KEY")
SUPABASE_PROPOSAL_BUCKET = os.getenv("SUPABASE_PROPOSAL_BUCKET", "proposal-formats")

app = FastAPI(title="Tender Proposal API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /login ─────────────────────────────────────────────────────────────────────

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        response = supabase.table("companies").select("*").eq("contact_email", email).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="User not found")
        logger.debug("Login response.data length: %s", len(response.data))
        logger.debug("Accessing login response.data index: 0")
        company = response.data[0]
        if not verify_password(password, company["password"]):
            raise HTTPException(status_code=401, detail="Invalid password")
        return {
            "status": "success",
            "company_id": company["id"],
            "company_name": company["company_name"],
            "industry": company.get("industry", ""),
            "contact_email": company.get("contact_email", email),
            "contact_phone": company.get("contact_phone", ""),
            "knowledge_base_path": company.get("knowledge_base_url", ""),
            "template_path": company.get("proposal_template_url", ""),
            "knowledge_base_name": _filename_from_storage_path(company.get("knowledge_base_url")),
            "proposal_template_name": _filename_from_storage_path(company.get("proposal_template_url")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /onboard-company ───────────────────────────────────────────────────────────

@app.post("/onboard-company")
async def onboard_company(
    company_name: str = Form(...),
    industry: str = Form(...),
    contact_email: str = Form(...),
    contact_phone: str = Form(...),
    password: str = Form(...),
    knowledge_base: UploadFile = File(...),
    proposal_template: UploadFile = File(...),
):
    company_id = str(uuid.uuid4())

    kb_path = upload_file_to_supabase(knowledge_base, bucket_name="company-documents", folder_name=company_id)
    template_path = upload_file_to_supabase(proposal_template, bucket_name="company-documents", folder_name=company_id)

    supabase.table("companies").insert({
        "id": company_id,
        "company_name": company_name,
        "industry": industry,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "password": hash_password(password),
        "knowledge_base_url": kb_path,
        "proposal_template_url": template_path,
    }).execute()

    # ── Embed knowledge base into Qdrant ──────────────────────────
    kb_bytes = supabase.storage.from_("company-documents").download(kb_path)
    file_ext = kb_path.split(".")[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
        tmp.write(kb_bytes)
        temp_kb_path = tmp.name

    # Convert DOCX → PDF only for the knowledge base (parser expects PDF)
    if temp_kb_path.endswith(".docx"):
        temp_kb_path = convert_docx_to_pdf(temp_kb_path)

    parsed_doc = run_parsing_pipeline(pdf_path=temp_kb_path)
    chunks = run_chunking_pipeline(parsed_doc)
    for chunk in chunks:
        chunk.metadata["company_id"] = company_id

    run_embedding_pipeline(
        chunks=chunks,
        doc_id=company_id,
        cohere_key=COHERE_KEY,
        qdrant_url=QDRANT_URL,
        qdrant_key=QDRANT_KEY,
        collection_name="company_knowledge",
    )
    logger.info("Company knowledge embedded: %s chunks", len(chunks))

    return {
        "status": "success",
        "company_id": company_id,
        "company_name": company_name,
        "industry": industry,
        "contact_email": contact_email,
        "contact_phone": contact_phone,
        "knowledge_base_path": kb_path,
        "template_path": template_path,
        "knowledge_base_name": knowledge_base.filename,
        "proposal_template_name": proposal_template.filename,
    }


# ── /upload-pdf ────────────────────────────────────────────────────────────────

@app.post("/update-company-assets")
async def update_company_assets(
    company_id: str = Form(...),
    knowledge_base: Optional[UploadFile] = File(None),
    proposal_template: Optional[UploadFile] = File(None),
):
    if knowledge_base is None and proposal_template is None:
        raise HTTPException(status_code=400, detail="Upload a knowledge base or proposal template to update")

    try:
        company_response = supabase.table("companies").select("*").eq("id", company_id).execute()
        if not company_response.data:
            raise HTTPException(status_code=404, detail="Company not found")

        update_payload = {}
        response_payload = {
            "status": "success",
            "company_id": company_id,
        }

        if knowledge_base is not None:
            kb_path = upload_file_to_supabase(
                knowledge_base,
                bucket_name="company-documents",
                folder_name=company_id,
            )
            embedding_result = _embed_company_knowledge(kb_path, company_id, replace_existing=True)
            update_payload["knowledge_base_url"] = kb_path
            response_payload.update({
                "knowledge_base_path": kb_path,
                "knowledge_base_name": knowledge_base.filename,
                "knowledge_chunks": embedding_result.get("total_chunks"),
            })

        if proposal_template is not None:
            template_path = upload_file_to_supabase(
                proposal_template,
                bucket_name="company-documents",
                folder_name=company_id,
            )
            update_payload["proposal_template_url"] = template_path
            response_payload.update({
                "template_path": template_path,
                "proposal_template_name": proposal_template.filename,
            })

        supabase.table("companies").update(update_payload).eq("id", company_id).execute()
        return response_payload

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Company asset update failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-pdf")
async def upload_pdf(company_id: str = Form(...), file: UploadFile = File(...)):

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")

    try:
        file_id = str(uuid.uuid4())[:8]
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file.file.seek(0)
        tender_path = upload_file_to_supabase(file, bucket_name="tender-documents", folder_name=company_id)

        # Parse tender
        parsed_doc = run_parsing_pipeline(pdf_path=file_path)

        # Detect if tender contains a proposal format/table
        proposal_sections = detect_proposal_formats_with_llm(parsed_doc)
        proposal_found = bool(proposal_sections)
        proposal_pdf_path = None
        extracted_pdf_path = None
        proposal_json = None
        format_count = len(proposal_sections)
        detected_format_types = [
            getattr(section, "format_type", "other_fill_format")
            for section in proposal_sections
        ]
        detection_method = (
            "keyword_fallback"
            if any(getattr(section, "detection_method", "") == "keyword_fallback" for section in proposal_sections)
            else "llm"
        )
        normalisation_applied = False

        if proposal_found:
            proposal_pdf_path = extract_proposal_pdf(file_path, proposal_sections, parsed_doc)
            if proposal_pdf_path:
                extracted_pdf_path = upload_file_to_supabase(
                    proposal_pdf_path,
                    bucket_name=SUPABASE_PROPOSAL_BUCKET,
                    folder_name=f"{company_id}/{parsed_doc.doc_id}",
                )
                parsed_proposal = run_parsing_pipeline(proposal_pdf_path)
                raw_proposal_json = build_proposal_json(parsed_proposal)
                proposal_json = validate_and_normalise_proposal_json(raw_proposal_json)
                normalisation_applied = proposal_json is not raw_proposal_json
            else:
                proposal_found = False
                format_count = 0
                detected_format_types = []

        # Chunk + embed tender
        chunks = run_chunking_pipeline(parsed_doc)
        for chunk in chunks:
            chunk.metadata["company_id"] = company_id

        result = run_embedding_pipeline(
            chunks=chunks,
            doc_id=parsed_doc.doc_id,
            cohere_key=COHERE_KEY,
            qdrant_url=QDRANT_URL,
            qdrant_key=QDRANT_KEY,
        )

        # Store tender in DB
        tender_id = str(uuid.uuid4())
        supabase.table("tenders").insert({
            "id": tender_id,
            "company_id": company_id,
            "doc_id": parsed_doc.doc_id,
            "tender_file_url": tender_path,
            "proposal_found": proposal_found,
            "proposal_json": proposal_json,
            "extracted_pdf_path": extracted_pdf_path,
            "format_count": format_count,
            "detected_format_types": detected_format_types,
            "detection_method": detection_method,
            "normalisation_applied": normalisation_applied,
        }).execute()

        sample_chunks = [
            {
                "chunk_id": c.chunk_id,
                "text_preview": c.text[:200],
                "is_table": c.is_table,
                "page_start": c.metadata.get("page_start"),
            }
            for c in chunks[:5]
        ]

        return {
            "status": "success",
            "doc_id": parsed_doc.doc_id,
            "total_chunks": len(chunks),
            "text_chunks": result["text_chunks"],
            "table_chunks": result["table_chunks"],
            "vectors_stored": result["vectors_stored"],
            "duration_seconds": result["duration_seconds"],
            "proposal_found": proposal_found,
            "proposal_pdf_path": str(proposal_pdf_path) if proposal_pdf_path else None,
            "extracted_pdf_path": extracted_pdf_path,
            "proposal_json": proposal_json,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── /generate-proposal ─────────────────────────────────────────────────────────

@app.post("/generate-proposal")
async def generate_proposal(
    company_id: str = Form(...),
    doc_id: str = Form(...),
    # NEW: "tender" = use format found in the tender PDF itself
    #      "template" = use the company's onboarded proposal template
    format_source: str = Form(default="tender"),
):
    try:
        logger.info("Starting proposal generation | format_source=%s", format_source)

        # ── Fetch tender row ───────────────────────────────────────
        tender_response = supabase.table("tenders").select("*").eq("doc_id", doc_id).execute()
        if not tender_response.data:
            raise HTTPException(status_code=404, detail="Tender not found")

        logger.debug("Tender response.data length: %s", len(tender_response.data))
        logger.debug("Accessing tender_response.data index: 0")
        tender_row = tender_response.data[0]

        # ── Determine proposal_json based on format_source ─────────
        proposal_json = None

        if format_source == "tender":
            # Use format embedded in the tender document
            proposal_found = tender_row.get("proposal_found", False)
            proposal_json = tender_row.get("proposal_json")

            if not proposal_found or not proposal_json:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "No proposal format found in this tender document. "
                        "Please use format_source='template' to use your onboarded template instead."
                    ),
                )
            logger.info("Using proposal format from tender document")

        else:
            # format_source == "template" — use company onboarded template
            logger.info("Using company onboarded template")

            company_response = supabase.table("companies").select(
                "proposal_template_url"
            ).eq("id", company_id).execute()

            if not company_response.data:
                raise HTTPException(status_code=404, detail="Company not found")

            logger.debug("Company response.data length: %s", len(company_response.data))
            logger.debug("Accessing company_response.data index: 0")
            template_url = company_response.data[0].get("proposal_template_url")
            if not template_url:
                raise HTTPException(status_code=400, detail="Company proposal template URL is missing")

            # Download template bytes
            template_bytes = supabase.storage.from_("company-documents").download(template_url)
            file_ext = template_url.split(".")[-1].lower()

            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_ext}") as tmp:
                tmp.write(template_bytes)
                temp_template_path = tmp.name

            # ── KEY FIX: parse DOCX directly (not via PDF conversion) ──
            # PDF conversion destroys table structure!
            if temp_template_path.endswith(".docx"):
                proposal_json = build_proposal_json_from_docx(temp_template_path)
                logger.info("Parsed DOCX template: %s sections", len(proposal_json.get("sections", [])))

            else:
                # It's a PDF template — use existing pipeline
                parsed_template = run_parsing_pipeline(pdf_path=temp_template_path)
                proposal_json = build_proposal_json(parsed_template)

        if not proposal_json:
            raise HTTPException(status_code=500, detail="Failed to build proposal_json")

        # ── Run LangGraph ──────────────────────────────────────────
        logger.info("Running LangGraph")

        graph = build_graph()

        initial_state = {
            "company_id": company_id,
            "doc_id": doc_id,
            "format_source": format_source,
            "proposal_json": proposal_json,
            "proposal_sections": [],
            "generated_sections": [],
            "current_section": {},
            "context": [],
            "section_index": 0,
            "status": "starting",
            "skip_section": False,
            "mode": "paragraph",  # will be overwritten by load_sections_node
            "output_file": "",
            "error": None,
        }

        result = graph.invoke(initial_state)

        logger.info("Graph execution complete")

        output_file = result.get("output_file")

        if not output_file or not os.path.exists(output_file):
            raise HTTPException(status_code=500, detail="Output file missing or not generated")

        logger.info("Returning file: %s", output_file)

        return FileResponse(
            path=output_file,
            filename="generated_proposal.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Proposal generation failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── /check-proposal-format ─────────────────────────────────────────────────────
# Utility endpoint — frontend calls this after upload to know which radio button
# to pre-select (tender format found vs must use template)

@app.get("/check-proposal-format")
async def check_proposal_format(doc_id: str):
    """
    Returns whether the uploaded tender contains its own proposal format.
    Frontend uses this to pre-select the format_source radio button.
    """
    try:
        response = supabase.table("tenders").select(
            "proposal_found, proposal_json"
        ).eq("doc_id", doc_id).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="Tender not found")

        logger.debug("check_proposal_format response.data length: %s", len(response.data))
        logger.debug("Accessing check_proposal_format response.data index: 0")
        row = response.data[0]
        return {
            "doc_id": doc_id,
            "proposal_found": row.get("proposal_found", False),
            "has_tables": _has_tables(row.get("proposal_json")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _has_tables(proposal_json) -> bool:
    if not proposal_json:
        return False
    for section in proposal_json.get("sections", []):
        if section.get("tables"):
            return True
    return False
