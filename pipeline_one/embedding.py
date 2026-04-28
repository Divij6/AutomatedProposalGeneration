from pipeline_one.parsing.pipeline   import run_parsing_pipeline
from pipeline_one.chunking.pipeline  import run_chunking_pipeline
from pipeline_one.embedding.pipeline import run_embedding_pipeline

PDF_PATH   = r"D:\Third Year\Projects\DataExtraction\documents\6565dbb36c16dTenderdoc144.pdf"
COHERE_KEY = "prRZFhvcguOv8Ss4svLYWN8kGCGYypdF5hh3pXZV"
QDRANT_URL = "https://e1a408b9-18aa-46f7-a3f7-fcfbebb20345.sa-east-1-0.aws.cloud.qdrant.io:6333"
QDRANT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.mlaWJmy3OGwF-p29vJjWB-3OmJLXkoSPCsvPDw4d1Eo"

# ── Run all 3 phases ──────────────────────────────────────────────────────────
parsed_doc = run_parsing_pipeline(PDF_PATH)
chunks     = run_chunking_pipeline(parsed_doc)
result     = run_embedding_pipeline(
    chunks     = chunks,
    doc_id     = parsed_doc.doc_id,
    cohere_key = COHERE_KEY,
    qdrant_url = QDRANT_URL,
    qdrant_key = QDRANT_KEY,
)

# ── Print result ──────────────────────────────────────────────────────────────
print(f"\nTotal chunks embedded : {result['total_chunks']}")
print(f"Text chunks           : {result['text_chunks']}")
print(f"Table chunks          : {result['table_chunks']}")
print(f"Vectors stored        : {result['vectors_stored']}")
print(f"Total in collection   : {result['vectors_in_collection']}")
print(f"Duration              : {result['duration_seconds']}s")
