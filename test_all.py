from ingestion.pdf_loader import load_pdf
from ingestion.chunker import chunk_text
from ingestion.indexer import index_chunks
from retrieval.search import search

print("load pdf...")
text = load_pdf("data/pdfs/test.pdf")

print("chunk...")
chunks = chunk_text(text)

print("index...")
index_chunks(chunks)

print("search...")
res = search("抗战精神是什么")

print("result:")
for r in res:
    print("\n---\n")
    print(r)