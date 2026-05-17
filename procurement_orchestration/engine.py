from __future__ import annotations

import json
import logging
import os
import re
import smtplib
import uuid
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from statistics import mean
from typing import Any

import cohere
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from config import COHERE_KEY, QDRANT_KEY, QDRANT_URL
from pipeline_one.embedding.cohere_embedder import embed_query
from pipeline_one.utils.supabase_client import supabase

logger = logging.getLogger(__name__)

FALLBACK_VENDOR_DIRECTORY = [
    {
        "vendor_id": "electrical_prime",
        "name": "Prime Electrical Supplies",
        "email": "rfq@prime-electrical.example",
        "categories": ["cable", "panel", "transformer", "switchgear", "electrical"],
        "rating": 4.7,
    },
    {
        "vendor_id": "civil_materials",
        "name": "BuildCore Materials",
        "email": "quotes@buildcore.example",
        "categories": ["cement", "steel", "aggregate", "civil", "construction"],
        "rating": 4.5,
    },
    {
        "vendor_id": "it_systems",
        "name": "Nexa IT Systems",
        "email": "tenders@nexait.example",
        "categories": ["server", "software", "network", "license", "cloud", "it"],
        "rating": 4.6,
    },
    {
        "vendor_id": "general_procurement",
        "name": "Universal Procurement Desk",
        "email": "sourcing@universal-procurement.example",
        "categories": ["general", "supply", "service", "equipment"],
        "rating": 4.2,
    },
]


def run_active_procurement_orchestration(
    *,
    company_id: str,
    doc_id: str,
    proposal_json: dict[str, Any],
    generated_sections: list[dict[str, Any]],
    company_name: str = "",
    tender_row: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tender_row = tender_row or {}
    requirements = _extract_requirements(proposal_json)
    vendor_directory = _load_vendor_directory()
    negotiation = _build_negotiation_plan(requirements, vendor_directory, company_name, doc_id)
    compliance = _score_compliance(requirements, generated_sections)
    reuse = _build_reuse_intelligence(requirements, company_id)
    deadlines = _build_deadline_orchestration(proposal_json, tender_row)

    result = {
        "run_id": str(uuid.uuid4()),
        "company_id": company_id,
        "company_name": company_name,
        "doc_id": doc_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "summary": {
            "requirements_detected": len(requirements),
            "vendor_rfq_count": sum(len(item["vendors_contacted"]) for item in negotiation),
            "average_compliance": round(compliance["average_score"], 2),
            "reuse_candidates": len(reuse["similar_tenders"]),
            "deadline_alerts": len(deadlines["reminders"]),
        },
        "requirements": requirements,
        "multi_agent_negotiation": negotiation,
        "compliance_scoring": compliance,
        "similarity_reuse_intelligence": reuse,
        "deadline_orchestration": deadlines,
    }

    _persist_result(company_id, doc_id, result)
    logger.info("Active procurement orchestration created for doc_id=%s", doc_id)
    return result


def get_orchestration_status(doc_id: str) -> dict[str, Any] | None:
    response = supabase.table("orchestration_runs").select("result").eq("doc_id", doc_id).limit(1).execute()
    if not response.data:
        return None
    return response.data[0].get("result")


def _persist_result(company_id: str, doc_id: str, result: dict[str, Any]) -> None:
    supabase.table("orchestration_runs").upsert(
        {
            "run_id": result["run_id"],
            "company_id": company_id,
            "doc_id": doc_id,
            "created_at": result["created_at"],
            "status": result["status"],
            "result": result,
        },
        on_conflict="doc_id",
    ).execute()


def _load_vendor_directory() -> list[dict[str, Any]]:
    try:
        response = supabase.table("vendors").select(
            "vendor_id, name, email, categories, rating"
        ).execute()
        vendors = response.data or []
        if vendors:
            return [
                {
                    "vendor_id": vendor.get("vendor_id"),
                    "name": vendor.get("name"),
                    "email": vendor.get("email"),
                    "categories": _normalise_categories(vendor.get("categories")),
                    "rating": float(vendor.get("rating") or 0),
                }
                for vendor in vendors
                if vendor.get("vendor_id") and vendor.get("name")
            ]
    except Exception:
        logger.exception("Vendor directory lookup failed; using fallback vendors")
    return FALLBACK_VENDOR_DIRECTORY


def _normalise_categories(raw_categories: Any) -> list[str]:
    if isinstance(raw_categories, list):
        return [str(item).strip().lower() for item in raw_categories if str(item).strip()]
    if isinstance(raw_categories, str):
        return [item.strip().lower() for item in raw_categories.split(",") if item.strip()]
    return ["general"]


def _extract_requirements(proposal_json: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = []
    for section_index, section in enumerate(proposal_json.get("sections", []) or []):
        section_title = str(section.get("title") or f"Section {section_index + 1}").strip()
        tables = section.get("tables") or []

        if tables:
            for table_index, table in enumerate(tables):
                headers = table.get("headers") or []
                rows = table.get("rows") or table.get("sample_rows") or []
                for row_index, row in enumerate(rows):
                    text = _best_requirement_text(headers, row)
                    if not text:
                        continue
                    requirements.append(_requirement_record(
                        text=text,
                        section_title=section_title,
                        section_index=section_index,
                        table_index=table_index,
                        row_index=row_index,
                    ))
        else:
            preview = str(section.get("text_preview") or "").strip()
            text = preview or section_title
            requirements.append(_requirement_record(
                text=text,
                section_title=section_title,
                section_index=section_index,
            ))

    return requirements[:80]


def _best_requirement_text(headers: list[Any], row: list[Any]) -> str:
    if not row:
        return ""
    header_text = " ".join(str(item).lower() for item in headers)
    preferred_indexes = []
    for idx, header in enumerate(headers):
        h = str(header).lower()
        if "required" in h or "specification" in h or "description" in h or "item" in h:
            preferred_indexes.append(idx)

    candidates = []
    for idx in preferred_indexes + list(range(len(row))):
        if idx < len(row):
            value = str(row[idx]).strip()
            if value and value.lower() not in {"yes", "no", "na", "n/a"}:
                candidates.append(value)

    if not candidates and header_text:
        candidates.append(header_text)
    return max(candidates, key=len, default="").strip()


def _requirement_record(
    *,
    text: str,
    section_title: str,
    section_index: int,
    table_index: int | None = None,
    row_index: int | None = None,
) -> dict[str, Any]:
    category = _classify_category(text)
    return {
        "requirement_id": f"REQ-{len(text)}-{section_index}-{table_index if table_index is not None else 'S'}-{row_index if row_index is not None else 'P'}",
        "title": text[:140],
        "requirement_text": text,
        "category": category,
        "section_title": section_title,
        "section_index": section_index,
        "table_index": table_index,
        "row_index": row_index,
        "priority": _priority_for(text),
    }


def _classify_category(text: str) -> str:
    lowered = text.lower()
    category_keywords = {
        "electrical": ["cable", "panel", "transformer", "switchgear", "voltage", "electrical"],
        "civil": ["cement", "steel", "concrete", "foundation", "civil", "construction"],
        "it": ["server", "software", "network", "license", "cloud", "security", "database"],
        "logistics": ["delivery", "transport", "packaging", "warehouse", "dispatch"],
        "service": ["maintenance", "support", "training", "installation", "commissioning"],
    }
    for category, keywords in category_keywords.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "general"


def _priority_for(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ["mandatory", "shall", "must", "critical"]):
        return "high"
    if any(token in lowered for token in ["should", "preferred", "desirable"]):
        return "medium"
    return "normal"


def _build_negotiation_plan(
    requirements: list[dict[str, Any]],
    vendor_directory: list[dict[str, Any]],
    company_name: str,
    doc_id: str,
) -> list[dict[str, Any]]:
    plan = []
    for requirement in requirements:
        vendors = _match_vendors(requirement, vendor_directory)
        quotes = []
        dispatches = []

        for vendor in vendors:
            quote = _quote_placeholder(requirement, vendor)
            quotes.append(quote)
            dispatches.append(_vendor_dispatch(requirement, vendor, company_name, doc_id, quote))

        priced_quotes = [quote for quote in quotes if quote.get("estimated_total") is not None]
        best_quote = min(priced_quotes, key=lambda item: item["estimated_total"], default=None)
        agent_name = f"{requirement['category'].title()} Negotiation Agent"
        plan.append({
            "requirement_id": requirement["requirement_id"],
            "agent": agent_name,
            "status": "rfq_dispatched" if vendors else "vendor_research_needed",
            "vendors_contacted": dispatches,
            "quotes_compared": quotes,
            "best_quote": best_quote,
            "proposal_feedback": _proposal_feedback(best_quote),
        })
    return plan


def _match_vendors(requirement: dict[str, Any], vendors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    category = requirement["category"]
    matched = [
        vendor for vendor in vendors
        if category in vendor.get("categories", []) or "general" in vendor.get("categories", [])
    ]
    return sorted(matched, key=lambda item: item.get("rating", 0), reverse=True)[:3]


def _vendor_dispatch(
    requirement: dict[str, Any],
    vendor: dict[str, Any],
    company_name: str,
    doc_id: str,
    quote: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "vendor_id": vendor.get("vendor_id"),
        "vendor_name": vendor.get("name"),
        "email": vendor.get("email"),
        "dispatch_status": "queued",
        "channel": "smtp_email",
        "quote_id": quote.get("quote_id"),
        "subject": f"RFQ for {company_name or 'Bidder'} tender requirement {requirement['requirement_id']}",
        "message": (
            f"Please quote for tender {doc_id}: {requirement['requirement_text']}. "
            f"Quote reference: {quote.get('quote_id')}. Include price, delivery lead time, validity, warranty, and compliance references."
        ),
    }
    payload["dispatch_status"] = _dispatch_rfq(payload)
    return payload


def _dispatch_rfq(payload: dict[str, Any]) -> str:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587") or "587")
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    recipient = str(payload.get("email") or "").strip()

    if not (smtp_host and smtp_user and smtp_pass and recipient):
        logger.warning("SMTP config or recipient missing for RFQ dispatch | vendor=%s", payload.get("vendor_id"))
        return "failed"

    message = EmailMessage()
    message["Subject"] = payload.get("subject", "RFQ Request")
    message["From"] = smtp_user
    message["To"] = recipient
    message.set_content(payload.get("message", ""))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(message)
        return "sent"
    except Exception:
        logger.exception("RFQ dispatch failed | vendor=%s | quote_id=%s", payload.get("vendor_id"), payload.get("quote_id"))
        return "failed"


def _quote_placeholder(requirement: dict[str, Any], vendor: dict[str, Any]) -> dict[str, Any]:
    quote_id = str(uuid.uuid4())
    record = {
        "quote_id": quote_id,
        "requirement_id": requirement["requirement_id"],
        "vendor_id": vendor.get("vendor_id"),
        "estimated_total": None,
        "currency": "INR",
        "lead_time_days": None,
        "validity_days": None,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        supabase.table("vendor_quotes").insert(record).execute()
    except Exception:
        logger.exception(
            "Failed to create pending vendor quote | requirement_id=%s | vendor_id=%s",
            requirement["requirement_id"],
            vendor.get("vendor_id"),
        )
        record["status"] = "insert_failed"
    return record


def _proposal_feedback(best_quote: dict[str, Any] | None) -> str:
    if not best_quote:
        return "No confirmed vendor quote is available yet; keep the commercial response marked for sourcing follow-up."
    if best_quote.get("estimated_total") is None:
        return f"Await vendor submission for quote {best_quote.get('quote_id')} before locking the commercial response."
    return (
        f"Use {best_quote['vendor_id']} as the current benchmark at "
        f"{best_quote['currency']} {best_quote['estimated_total']} with "
        f"{best_quote['lead_time_days']} days lead time, pending final confirmation."
    )


def _score_compliance(
    requirements: list[dict[str, Any]],
    generated_sections: list[dict[str, Any]],
) -> dict[str, Any]:
    section_docs = [
        {
            "title": str(section.get("title", "")).strip(),
            "content": str(section.get("content", "")).strip(),
        }
        for section in generated_sections
        if str(section.get("content", "")).strip()
    ]
    client = cohere.ClientV2(api_key=COHERE_KEY) if COHERE_KEY else None
    scored = []

    for requirement in requirements:
        response = ""
        matched_title = requirement["section_title"]
        score = 0

        if client and section_docs:
            try:
                rerank_response = client.rerank(
                    model="rerank-multilingual-v3.0",
                    query=requirement["requirement_text"],
                    documents=[section["content"] for section in section_docs],
                    top_n=1,
                )
                rerank_results = getattr(rerank_response, "results", None) or []
                if rerank_results:
                    top_result = rerank_results[0]
                    result_index = int(getattr(top_result, "index", 0) or 0)
                    matched_doc = section_docs[result_index]
                    response = matched_doc["content"]
                    matched_title = matched_doc["title"] or matched_title
                    relevance_score = float(getattr(top_result, "relevance_score", 0) or 0)
                    score = round(max(0.0, min(1.0, relevance_score)) * 100)
            except Exception:
                logger.exception("Compliance rerank failed | requirement_id=%s", requirement["requirement_id"])
        elif section_docs:
            response = _closest_generated_text(requirement, {
                section["title"].lower(): section["content"] for section in section_docs
            })

        scored.append({
            "requirement_id": requirement["requirement_id"],
            "section_title": matched_title,
            "requirement": requirement["requirement_text"],
            "matched_response": response,
            "score": score,
            "status": "compliant" if score >= 80 else "needs_review" if score >= 55 else "gap",
            "recommendation": _compliance_recommendation(score),
        })

    scores = [item["score"] for item in scored]
    return {
        "average_score": mean(scores) if scores else 0,
        "sections": scored,
    }


def _closest_generated_text(requirement: dict[str, Any], section_text: dict[str, str]) -> str:
    section_key = requirement["section_title"].lower()
    if section_key in section_text:
        return section_text[section_key]

    best = ""
    best_overlap = -1
    requirement_terms = {
        token for token in re.findall(r"[a-zA-Z0-9]{4,}", requirement["requirement_text"].lower())
    }
    for text in section_text.values():
        candidate_terms = {
            token for token in re.findall(r"[a-zA-Z0-9]{4,}", text.lower())
        }
        overlap = len(requirement_terms.intersection(candidate_terms))
        if overlap > best_overlap:
            best = text
            best_overlap = overlap
    return best


def _compliance_recommendation(score: int) -> str:
    if score >= 80:
        return "Ready for reviewer confirmation."
    if score >= 55:
        return "Add stronger clause-specific evidence before submission."
    return "Escalate to bid manager; response does not sufficiently cover the tender requirement."


def _build_reuse_intelligence(
    requirements: list[dict[str, Any]],
    company_id: str,
) -> dict[str, Any]:
    combined_query = "\n".join(
        requirement["requirement_text"] for requirement in requirements if requirement.get("requirement_text")
    ).strip()
    if not combined_query or not (COHERE_KEY and QDRANT_URL):
        return {"similar_tenders": [], "learning_actions": []}

    try:
        query_vector = embed_query(combined_query, COHERE_KEY)
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=60)
        response = client.query_points(
            collection_name="company_knowledge",
            query=query_vector,
            limit=5,
            with_payload=True,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="company_id",
                        match=MatchValue(value=company_id),
                    )
                ]
            ),
        ).points
        similar = []
        for point in response:
            payload = point.payload or {}
            similar.append({
                "source_document_id": payload.get("doc_id"),
                "section_title": payload.get("section_title"),
                "similarity_score": round(float(getattr(point, "score", 0) or 0), 4),
                "text_preview": str(payload.get("text", ""))[:300],
            })
        return {
            "similar_tenders": similar,
            "learning_actions": [
                "Promote high-similarity reusable chunks into future proposal context.",
                "Prioritise reviewed reusable knowledge when drafting technical sections.",
            ],
        }
    except Exception:
        logger.exception("Reuse intelligence lookup failed")
        return {"similar_tenders": [], "learning_actions": []}


def _build_deadline_orchestration(
    proposal_json: dict[str, Any],
    tender_row: dict[str, Any],
) -> dict[str, Any]:
    deadline = _extract_deadline(proposal_json, tender_row)
    reminders = []
    if deadline:
        for days_before, owner, action in [
            (7, "Bid Manager", "Confirm all vendor quotes and commercial annexures."),
            (3, "Compliance Reviewer", "Complete section-by-section compliance review."),
            (1, "Submission Owner", "Freeze final files and prepare portal submission."),
        ]:
            remind_at = deadline - timedelta(days=days_before)
            reminders.append({
                "remind_at": remind_at.isoformat(),
                "owner": owner,
                "action": action,
                "escalation": "Escalate to leadership if unresolved after 4 business hours.",
            })
    else:
        reminders.append({
            "remind_at": datetime.now(timezone.utc).isoformat(),
            "owner": "Bid Manager",
            "action": "Tender deadline not detected; enter submission date manually.",
            "escalation": "Escalate immediately because schedule automation needs a deadline.",
        })
    return {
        "submission_deadline": deadline.isoformat() if deadline else None,
        "reminders": reminders,
    }


def _extract_deadline(proposal_json: dict[str, Any], tender_row: dict[str, Any]) -> datetime | None:
    for key in ["submission_deadline", "deadline", "due_date"]:
        value = tender_row.get(key) or proposal_json.get(key)
        if value:
            parsed = _parse_datetime(str(value))
            if parsed:
                return parsed

    text = json.dumps(proposal_json, ensure_ascii=False)
    match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b", text)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return datetime(year, month, day, 17, 0, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
