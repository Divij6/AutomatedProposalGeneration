# from qdrant_client import QdrantClient
# from qdrant_client.models import (
#     Filter,
#     FieldCondition,
#     MatchValue
# )
#
# from pipeline_one.embedding.cohere_embedder import embed_query
#
#
# def retrieve_section_context(
#
#     section_title: str,
#
#     company_id: str,
#
#     cohere_key: str,
#
#     qdrant_url: str,
#
#     qdrant_key: str,
#
#     top_k: int = 5
#
# ):
#
#     # Step 1 — Embed query
#     query_vector = embed_query(
#
#         text=section_title,
#
#         api_key=cohere_key
#
#     )
#
#     # Step 2 — Connect Qdrant
#     client = QdrantClient(
#
#         url=qdrant_url,
#
#         api_key=qdrant_key,
#
#     )
#
#     # Step 3 — Filter
#     company_filter = Filter(
#
#         must=[
#
#             FieldCondition(
#
#                 key="company_id",
#
#                 match=MatchValue(
#                     value=company_id
#                 )
#
#             )
#
#         ]
#
#     )
#
#     # Step 4 — Search company KB
#     company_results = client.query_points(
#
#         collection_name="company_knowledge",
#
#         query=query_vector,
#
#         limit=top_k,
#
#         query_filter=company_filter
#
#     )
#
#     # Step 5 — Search tender chunks
#     tender_results = client.query_points(
#
#         collection_name="tender_chunks",
#
#         query=query_vector,
#
#         limit=top_k,
#
#         query_filter=company_filter
#
#     )
#
#     combined_context = []
#     # Tender results
#     for r in tender_results.points:
#
#         text = r.payload.get("text")
#
#         if text:
#
#             combined_context.append({
#
#                 "source": "tender",
#
#                 "text": text
#
#             })
#     # Company results
#     for r in company_results.points:
#
#         text = r.payload.get("text")
#
#         if text:
#
#             combined_context.append({
#
#                 "source": "company",
#
#                 "text": text
#
#             })
#
#
#
#
#     return combined_context

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from pipeline_one.embedding.cohere_embedder import embed_chunks


def retrieve_section_context(

    section_title: str,
    company_id: str,
    cohere_key: str,
    qdrant_url: str,
    qdrant_key: str,
    top_k: int = 5,
    doc_id: str | None = None

):

    # -------------------------------
    # STEP 0 — Embed Query
    # -------------------------------

    query_chunk = type("Temp", (), {"text": section_title})

    query_vector = embed_chunks(
        [query_chunk],
        api_key=cohere_key
    )[0]

    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_key
    )

    # -------------------------------
    # Filter by company_id
    # -------------------------------

    company_filter = Filter(
        must=[
            FieldCondition(
                key="company_id",
                match=MatchValue(
                    value=company_id
                )
            )
        ]
    )

    tender_filter_conditions = [
        FieldCondition(
            key="company_id",
            match=MatchValue(value=company_id)
        )
    ]

    if doc_id:
        tender_filter_conditions.append(
            FieldCondition(
                key="doc_id",
                match=MatchValue(value=doc_id)
            )
        )

    tender_filter = Filter(must=tender_filter_conditions)

    # -------------------------------
    # STEP 1 — Retrieve Tender Chunks
    # -------------------------------

    tender_results = client.query_points(

        collection_name="tender_chunks",

        query=query_vector,   # ✅ FIXED

        limit=top_k,

        query_filter=tender_filter

    ).points   # ✅ IMPORTANT

    # -------------------------------
    # STEP 2 — Neighbor Expansion
    # -------------------------------

    expanded_chunks = []

    for r in tender_results:

        payload = r.payload

        expanded_chunks.append(payload)

        chunk_id = payload.get("chunk_id")
        doc_id = payload.get("doc_id")

        if chunk_id is None:
            continue

        # Extract numeric part
        try:
            numeric_id = int(chunk_id.split("_")[1])
        except:
            continue

        # Build neighbor IDs
        neighbor_ids = [

            f"c_{numeric_id - 1:05d}",
            f"c_{numeric_id + 1:05d}"

        ]

        for nid in neighbor_ids:

            try:

                neighbor_points, _ = client.scroll(

                    collection_name="tender_chunks",

                    scroll_filter=Filter(
                        must=[

                            FieldCondition(
                                key="doc_id",
                                match=MatchValue(
                                    value=doc_id
                                )
                            ),

                            FieldCondition(
                                key="chunk_id",
                                match=MatchValue(
                                    value=nid
                                )
                            )

                        ]
                    ),

                    limit=1

                )

                if neighbor_points:

                    expanded_chunks.append(
                        neighbor_points[0].payload
                    )

            except:
                pass

    # -------------------------------
    # STEP 3 — Company Knowledge
    # -------------------------------

    company_results = client.query_points(

        collection_name="company_knowledge",

        query=query_vector,   # ✅ FIXED

        limit=top_k,

        query_filter=company_filter

    ).points   # ✅ IMPORTANT

    # -------------------------------
    # STEP 4 — Combine Context
    # -------------------------------

    combined_context = []

    # Tender FIRST (priority)

    for c in expanded_chunks:

        combined_context.append({

            "source": "tender",

            "text": c.get("text", ""),

            "chunk_id": c.get("chunk_id"),

            "doc_id": c.get("doc_id"),

            "section_title": c.get("section_title"),

            "page_start": c.get("page_start"),

        })

    # Company SECOND

    for r in company_results:

        combined_context.append({

            "source": "company",

            "text": r.payload.get("text", ""),

            "chunk_id": r.payload.get("chunk_id"),

            "doc_id": r.payload.get("doc_id"),

            "section_title": r.payload.get("section_title"),

            "page_start": r.payload.get("page_start"),

        })

    # -------------------------------
    # STEP 5 — Remove Duplicates
    # -------------------------------

    seen = set()

    final_context = []

    for item in combined_context:

        text = item["text"]

        if text not in seen:

            seen.add(text)

            final_context.append(item)

    return final_context
