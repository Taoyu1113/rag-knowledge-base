from ingestion.pdf_loader import load_pdf
from ingestion.chunker import chunk_text
from ingestion.indexer import index_chunks


def run_pipeline():
    path = "data/pdfs/test.pdf"

    text = load_pdf(path)
    chunks = chunk_text(text)

    print("开始入库...")
    index_chunks(chunks)

    print("入库完成")


if __name__ == "__main__":
    run_pipeline()