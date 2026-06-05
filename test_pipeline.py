# -*- coding: utf-8 -*-
from ingestion.pdf_loader import load_pdf
from ingestion.chunker import chunk_text
from ingestion.indexer import index_chunks
from utils.text_clean import clean_text


def run_pipeline(pdf_path="data/pdfs/test.pdf"):
    print(f"加载 PDF: {pdf_path}")
    text = load_pdf(pdf_path)

    print("清洗文本...")
    text = clean_text(text)

    print("切分 chunk...")
    chunks = chunk_text(text)
    print(f"  共 {len(chunks)} 个 chunk")

    print("向量化并入库...")
    index_chunks(chunks, source=pdf_path)

    print("全部完成")


if __name__ == "__main__":
    run_pipeline()
