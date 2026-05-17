# from fastapi import FastAPI, UploadFile, File, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# import shutil
# import os
# import uuid
# from pathlib import Path
# from fastapi import UploadFile, File, Form
# import uuid
#
#
# # Your pipeline imports
# from pipeline_one.parsing.pipeline import run_parsing_pipeline
# from pipeline_one.chunking.pipeline import run_chunking_pipeline
# from pipeline_one.embedding.pipeline import run_embedding_pipeline
# from pipeline_one.proposal.detector import detect_proposal_sections
# from pipeline_one.proposal.extractor import extract_proposal_pdf
# from pipeline_one.proposal.json_builder import build_proposal_json
# from pipeline_one.utils.supabase_client import (
#     supabase,
#     upload_file_to_supabase
# )
#
# from docx import Document
# from reportlab.lib.pagesizes import letter
# from reportlab.platypus import SimpleDocTemplate, Paragraph
# from reportlab.lib.styles import getSampleStyleSheet
#
#
# def convert_docx_to_pdf(docx_path):
#
#     pdf_path = docx_path.replace(".docx", ".pdf")
#
#     doc = Document(docx_path)
#
#     styles = getSampleStyleSheet()
#
#     elements = []
#
#     for para in doc.paragraphs:
#
#         elements.append(
#             Paragraph(
#                 para.text,
#                 styles["Normal"]
#             )
#         )
#
#     pdf = SimpleDocTemplate(
#         pdf_path,
#         pagesize=letter
#     )
#
#     pdf.build(elements)
#
#     return pdf_path
#
# import bcrypt
#
#
# def hash_password(password: str) -> str:
#
#     salt = bcrypt.gensalt()
#
#     hashed = bcrypt.hashpw(
#         password.encode("utf-8"),
#         salt
#     )
#
#     return hashed.decode("utf-8")
#
# def verify_password(
#     plain_password: str,
#     hashed_password: str
# ) -> bool:
#
#     return bcrypt.checkpw(
#         plain_password.encode("utf-8"),
#         hashed_password.encode("utf-8")
#     )
#
# app = FastAPI(title="PDF Embedding Pipeline API")
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#         "http://localhost:4173",
#         "http://127.0.0.1:4173",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
#
#
# # ── CONFIG ─────────────────────────────────────────────
#
# UPLOAD_DIR = Path("uploaded_pdfs")
# UPLOAD_DIR.mkdir(exist_ok=True)
#
# COHERE_KEY = os.getenv("COHERE_KEY")
#
# QDRANT_URL = os.getenv("QDRANT_URL")
# QDRANT_KEY = os.getenv("QDRANT_KEY")
#
#
# # ── MAIN ENDPOINT ─────────────────────────────────────
# @app.post("/login")
#
# async def login(
#
#     email: str = Form(...),
#
#     password: str = Form(...)
#
# ):
#
#     try:
#
#         print("\nLogin attempt...\n")
#
#         # -----------------------------------
#         # Step 1 — Find Company by Email
#         # -----------------------------------
#
#         response = supabase.table(
#             "companies"
#         ).select(
#             "*"
#         ).eq(
#             "contact_email",
#             email
#         ).execute()
#
#         if not response.data:
#
#             raise HTTPException(
#
#                 status_code=404,
#
#                 detail="User not found"
#
#             )
#
#         company = response.data[0]
#
#         stored_password = company["password"]
#
#         # -----------------------------------
#         # Step 2 — Verify Password
#         # -----------------------------------
#
#         if not verify_password(
#
#             password,
#
#             stored_password
#
#         ):
#
#             raise HTTPException(
#
#                 status_code=401,
#
#                 detail="Invalid password"
#
#             )
#
#         print(
#             f"Login successful: {company['company_name']}"
#         )
#
#         # -----------------------------------
#         # Step 3 — Return company_id
#         # -----------------------------------
#
#         return {
#
#             "status": "success",
#
#             "company_id": company["id"],
#
#             "company_name": company["company_name"]
#
#         }
#
#     except Exception as e:
#
#         raise HTTPException(
#
#             status_code=500,
#
#             detail=str(e)
#
#         )
#
# @app.post("/upload-pdf")
# async def upload_pdf(company_id: str = Form(...), file: UploadFile = File(...)):
#
#     if not file.filename.endswith(".pdf"):
#         raise HTTPException(
#             status_code=400,
#             detail="Only PDF files allowed"
#         )
#
#     try:
#
#         # ── Save uploaded file ─────────────────
#
#         file_id = str(uuid.uuid4())[:8]
#
#         file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
#
#         with open(file_path, "wb") as buffer:
#             shutil.copyfileobj(file.file, buffer)
#         file.file.seek(0)
#         tender_path = upload_file_to_supabase(
#
#             file,
#
#             bucket_name="tender-documents",
#
#             folder_name=company_id
#
#         )
#         # ── Run Parsing ─────────────────
#
#         parsed_doc = run_parsing_pipeline(
#             pdf_path=file_path
#         )
#         # ── Detect Proposal ─────────────────
#
#         proposal_sections = detect_proposal_sections(
#             parsed_doc
#         )
#
#         proposal_found = False
#         proposal_pdf_path = None
#         proposal_json = None
#
#         if proposal_sections:
#             proposal_found = True
#
#             # Extract proposal PDF
#             proposal_pdf_path = extract_proposal_pdf(
#                 file_path,
#                 proposal_sections,
#                 parsed_doc
#             )
#
#             # Parse extracted proposal
#             parsed_proposal = run_parsing_pipeline(
#                 proposal_pdf_path
#             )
#
#             # Convert to JSON
#             proposal_json = build_proposal_json(
#                 parsed_proposal
#             )
#         # ── Run Chunking ─────────────────
#
#         chunks = run_chunking_pipeline(
#             parsed_doc
#         )
#         for chunk in chunks:
#             chunk.metadata["company_id"] = company_id
#         # ── Run Embedding ────────────────
#
#         result = run_embedding_pipeline(
#             chunks     = chunks,
#             doc_id     = parsed_doc.doc_id,
#             cohere_key = COHERE_KEY,
#             qdrant_url = QDRANT_URL,
#             qdrant_key = QDRANT_KEY,
#         )
#
#         # ── Prepare sample chunks ─────────
#
#         sample_chunks = []
#
#         for chunk in chunks[:5]:
#
#             sample_chunks.append({
#                 "chunk_id": chunk.chunk_id,
#                 "text_preview": chunk.text[:200],
#                 "is_table": chunk.is_table,
#                 "page_start": chunk.metadata.get("page_start")
#             })
#
#
#
#         # ------------------------------------
#         # Store tender metadata in Supabase
#         # ------------------------------------
#
#         tender_id = str(uuid.uuid4())
#
#         supabase.table("tenders").insert({
#
#             "id": tender_id,
#
#             "company_id": company_id,
#
#             "doc_id": parsed_doc.doc_id,
#
#             "tender_file_url": tender_path,
#
#             "proposal_found": proposal_found,
#
#             "proposal_json": proposal_json
#
#         }).execute()
#
#         print(
#             f"Tender stored in DB: {tender_id}"
#         )
#         # ── Return response ──────────────
#
#         return {
#
#             "status": "success",
#
#             "doc_id": parsed_doc.doc_id,
#
#             "total_chunks": len(chunks),
#
#             "text_chunks": result["text_chunks"],
#
#             "table_chunks": result["table_chunks"],
#
#             "vectors_stored": result["vectors_stored"],
#
#             "duration_seconds": result["duration_seconds"],
#
#             "proposal_found": proposal_found,
#
#             "proposal_pdf_path": (
#                 str(proposal_pdf_path)
#                 if proposal_pdf_path else None
#             ),
#
#             "proposal_json": proposal_json,
#
#         }
#
#     except Exception as e:
#
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )
#
#
#
# @app.post("/onboard-company")
# async def onboard_company(
#
#     company_name: str = Form(...),
#
#     industry: str = Form(...),
#
#     contact_email: str = Form(...),
#
#     contact_phone: str = Form(...),
#     password: str = Form(...),
#
#     knowledge_base: UploadFile = File(...),
#
#     proposal_template: UploadFile = File(...),
#
# ):
#
#     company_id = str(uuid.uuid4())
#
#     # Upload files
#     kb_path = upload_file_to_supabase(
#
#         knowledge_base,
#
#         bucket_name="company-documents",
#
#         folder_name=company_id
#
#     )
#
#     template_path = upload_file_to_supabase(
#
#         proposal_template,
#
#         bucket_name="company-documents",
#
#         folder_name=company_id
#
#     )
#     hashed_password = hash_password(password)
#     # Insert DB record
#     data = {
#
#         "id": company_id,
#
#         "company_name": company_name,
#
#         "industry": industry,
#
#         "contact_email": contact_email,
#
#         "contact_phone": contact_phone,
#         "password": hashed_password,
#
#         "knowledge_base_url": kb_path,
#
#         "proposal_template_url": template_path,
#
#     }
#
#     supabase.table("companies").insert(data).execute()
#     # --------------------------------------------------
#     # NEW: Process Knowledge Base into Qdrant
#     # --------------------------------------------------
#
#     import tempfile
#
#
#     # Step 1 — Download KB from Supabase
#     kb_bytes = supabase.storage.from_(
#         "company-documents"
#     ).download(kb_path)
#
#     # Detect file extension
#     file_ext = kb_path.split(".")[-1]
#
#     # Step 2 — Save temp file with correct extension
#     import tempfile
#
#     with tempfile.NamedTemporaryFile(
#             delete=False,
#             suffix=f".{file_ext}"
#     ) as tmp:
#         tmp.write(kb_bytes)
#
#         temp_kb_path = tmp.name
#
#     # Step 3 — Run Parsing
#     # Convert DOCX if needed
#     if temp_kb_path.endswith(".docx"):
#         temp_kb_path = convert_docx_to_pdf(
#             temp_kb_path
#         )
#
#     # Now run parser
#     parsed_doc = run_parsing_pipeline(
#         pdf_path=temp_kb_path
#     )
#
#     # Step 4 — Chunking
#     chunks = run_chunking_pipeline(
#         parsed_doc
#     )
#
#     # Step 5 — Add company_id metadata
#     for chunk in chunks:
#         chunk.metadata["company_id"] = company_id
#
#     # Step 6 — Embedding into company_knowledge
#     run_embedding_pipeline(
#
#         chunks=chunks,
#
#         doc_id=company_id,
#         cohere_key=COHERE_KEY,
#
#         qdrant_url=QDRANT_URL,
#
#         qdrant_key=QDRANT_KEY,
#         collection_name="company_knowledge"
#
#     )
#
#     print(
#         f"Company knowledge embedded: {len(chunks)} chunks"
#     )
#
#
#     return {
#
#         "status": "success",
#
#         "company_id": company_id,
#
#         "knowledge_base_path": kb_path,
#
#         "template_path": template_path
#
#     }
#
# from fastapi.responses import FileResponse
# from agents.graph import build_graph
#
#
# @app.post("/generate-proposal")
# async def generate_proposal(
#
#     company_id: str = Form(...),
#
#     doc_id: str = Form(...)
#
# ):
#
#     try:
#
#         print("\nStarting proposal generation...\n")
#
#         # -----------------------------------
#         # Step 1 — Fetch Tender Row
#         # -----------------------------------
#
#         tender_response = supabase.table(
#             "tenders"
#         ).select(
#             "*"
#         ).eq(
#             "doc_id",
#             doc_id
#         ).execute()
#
#         if not tender_response.data:
#
#             raise HTTPException(
#                 status_code=404,
#                 detail="Tender not found"
#             )
#
#         tender_row = tender_response.data[0]
#
#         proposal_found = tender_row[
#             "proposal_found"
#         ]
#
#         proposal_json = tender_row[
#             "proposal_json"
#         ]
#
#         print(
#             f"Proposal format found: {proposal_found}"
#         )
#
#         # -----------------------------------
#         # Step 2 — If No Format → Load Template
#         # -----------------------------------
#
#         if not proposal_found:
#
#             print(
#                 "No proposal format found — loading template"
#             )
#
#             company_response = supabase.table(
#                 "companies"
#             ).select(
#                 "proposal_template_url"
#             ).eq(
#                 "id",
#                 company_id
#             ).execute()
#
#             template_url = company_response.data[0][
#                 "proposal_template_url"
#             ]
#
#             # Download template
#             template_bytes = supabase.storage.from_(
#                 "company-documents"
#             ).download(
#                 template_url
#             )
#
#             import tempfile
#
#             with tempfile.NamedTemporaryFile(
#                 delete=False,
#                 suffix=".docx"
#             ) as tmp:
#
#                 tmp.write(template_bytes)
#
#                 temp_template_path = tmp.name
#
#             # Convert DOCX → PDF
#             if temp_template_path.endswith(".docx"):
#
#                 temp_template_path = convert_docx_to_pdf(
#                     temp_template_path
#                 )
#
#             # Parse template
#             parsed_template = run_parsing_pipeline(
#                 pdf_path=temp_template_path
#             )
#
#             # Convert to proposal JSON
#             proposal_json = build_proposal_json(
#                 parsed_template
#             )
#
#         # -----------------------------------
#         # Step 3 — Run LangGraph
#         # -----------------------------------
#
#         print("\nRunning LangGraph...\n")
#
#         graph = build_graph()
#
#         initial_state = {
#
#             "company_id": company_id,
#
#             "doc_id": doc_id,
#
#             "proposal_json": proposal_json,
#
#             "proposal_sections": [],
#
#             "generated_sections": [],
#
#             "current_section": {},
#
#             "context": [],
#
#             "section_index": 0,
#
#             "status": "starting",
#
#             "skip_section": False,
#
#             "output_file": ""
#
#         }
#
#         result = graph.invoke(
#             initial_state
#         )
#
#         print(
#             "\nGraph execution complete\n"
#         )
#
#         # -----------------------------------
#         # Step 4 — Return Generated File
#         # -----------------------------------
#
#         output_file = result.get(
#             "output_file"
#         )
#
#         if not output_file:
#
#             raise HTTPException(
#                 status_code=500,
#                 detail="Output file missing"
#             )
#
#         print(
#             f"Returning file: {output_file}"
#         )
#
#         return FileResponse(
#
#             path=output_file,
#
#             filename="generated_proposal.docx",
#
#             media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
#
#         )
#
#     except Exception as e:
#
#         raise HTTPException(
#             status_code=500,
#             detail=str(e)
#         )


from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import shutil
import os
import uuid
import tempfile
import logging
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
from procurement_orchestration import (
    get_orchestration_status,
    run_active_procurement_orchestration,
)

from agents.graph import build_graph

from docx import Document
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


# ── App setup ──────────────────────────────────────────────────────────────────

UPLOAD_DIR = Path("uploaded_pdfs")
UPLOAD_DIR.mkdir(exist_ok=True)
GENERATED_PROPOSAL_DIR = Path("generated_proposals")
GENERATED_PROPOSAL_DIR.mkdir(exist_ok=True)

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
        "knowledge_base_path": kb_path,
        "template_path": template_path,
    }


# ── /upload-pdf ────────────────────────────────────────────────────────────────

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

        company_name = "the Bidder"
        company_response = supabase.table("companies").select(
            "company_name, proposal_template_url"
        ).eq("id", company_id).execute()
        if company_response.data:
            company_name = company_response.data[0].get("company_name") or company_name

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
            "company_name": company_name,
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
            "output_file": str(
                GENERATED_PROPOSAL_DIR / f"{company_id}_{doc_id}_{uuid.uuid4().hex[:8]}.docx"
            ),
            "error": None,
        }

        result = graph.invoke(initial_state)

        logger.info("Graph execution complete")

        try:
            orchestration_result = run_active_procurement_orchestration(
                company_id=company_id,
                company_name=company_name,
                doc_id=doc_id,
                proposal_json=proposal_json,
                generated_sections=result.get("generated_sections", []),
                tender_row=tender_row,
            )
            logger.info(
                "Procurement orchestration triggered | run_id=%s",
                orchestration_result.get("run_id"),
            )
        except Exception:
            logger.exception("Post-generation procurement orchestration failed")

        output_file = result.get("output_file")

        if not output_file or not os.path.exists(output_file):
            raise HTTPException(status_code=500, detail="Output file missing or not generated")

        supabase.table("tenders").update({
            "proposal_file_path": output_file,
        }).eq("doc_id", doc_id).execute()

        logger.info("Returning file: %s", output_file)

        return FileResponse(
            path=output_file,
            filename=Path(output_file).name,
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


@app.get("/procurement-orchestration/{doc_id}")
async def procurement_orchestration_status(doc_id: str):
    result = get_orchestration_status(doc_id)
    if not result:
        raise HTTPException(status_code=404, detail="Procurement orchestration has not run for this tender")
    return result


@app.post("/trigger-procurement-orchestration")
async def trigger_procurement_orchestration(
    company_id: str = Form(...),
    doc_id: str = Form(...),
):
    try:
        tender_response = supabase.table("tenders").select("*").eq("doc_id", doc_id).execute()
        if not tender_response.data:
            raise HTTPException(status_code=404, detail="Tender not found")

        company_response = supabase.table("companies").select("company_name").eq("id", company_id).execute()
        company_name = (
            company_response.data[0].get("company_name")
            if company_response.data else "the Bidder"
        )
        tender_row = tender_response.data[0]
        proposal_json = tender_row.get("proposal_json")
        if not proposal_json:
            raise HTTPException(status_code=400, detail="Tender has no proposal_json to orchestrate")

        return run_active_procurement_orchestration(
            company_id=company_id,
            company_name=company_name,
            doc_id=doc_id,
            proposal_json=proposal_json,
            generated_sections=[],
            tender_row=tender_row,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Manual procurement orchestration trigger failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/submit-quote")
async def submit_quote(
    quote_id: str = Form(...),
    estimated_total: float = Form(...),
    currency: str = Form(...),
    lead_time_days: int = Form(...),
    validity_days: int = Form(...),
    status: str = Form(default="submitted"),
):
    try:
        response = supabase.table("vendor_quotes").update({
            "estimated_total": estimated_total,
            "currency": currency,
            "lead_time_days": lead_time_days,
            "validity_days": validity_days,
            "status": status,
        }).eq("quote_id", quote_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Quote not found")
        return {
            "status": "success",
            "quote": response.data[0],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Quote submission failed")
        raise HTTPException(status_code=500, detail=str(e))


def _has_tables(proposal_json) -> bool:
    if not proposal_json:
        return False
    for section in proposal_json.get("sections", []):
        if section.get("tables"):
            return True
    return False
