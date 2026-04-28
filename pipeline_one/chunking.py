from pipeline_one.parsing.pipeline  import run_parsing_pipeline
from pipeline_one.chunking.pipeline import run_chunking_pipeline

PDF_PATH = r"D:\Third Year\Projects\DataExtraction\documents\GeM-Bidding-8887545.pdf"

parsed_doc = run_parsing_pipeline(PDF_PATH)
chunks     = run_chunking_pipeline(parsed_doc)

print(f"\nTotal chunks : {len(chunks)}")
print(f"Text chunks  : {len([c for c in chunks if not c.is_table])}")
print(f"Table chunks : {len([c for c in chunks if c.is_table])}")

print("\n── First 3 chunks ──")
for chunk in chunks[:3]:
    print(f"\n[{chunk.chunk_id}] is_table={chunk.is_table} lang={chunk.language}")
    print(f"  section : {chunk.metadata.get('section_title')}")
    print(f"  pages   : {chunk.metadata.get('page_start')}→{chunk.metadata.get('page_end')}")
    print(f"  text    : {chunk.text[:150]}...")