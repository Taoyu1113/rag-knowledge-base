# -*- coding: utf-8 -*-
from ingestion.pdf_loader import load_pdf
from ingestion.chunker import chunk_text
from ingestion.indexer import index_chunks, collection
from retrieval.search import search
from utils.text_clean import clean_text


def run_all(pdf_path="data/pdfs/test.pdf", query="抗战精神是什么"):
    # 1. 加载
    print("1. 加载 PDF...")
    text = load_pdf(pdf_path)
    print(f"   文本长度: {len(text)} 字符")

    # 2. 清洗
    print("2. 清洗文本...")
    text = clean_text(text)

    # 3. 切分
    print("3. 切分 chunk...")
    chunks = chunk_text(text)
    print(f"   共 {len(chunks)} 个 chunk")

    # 4. 入库
    print("4. 向量化并入库...")
    index_chunks(chunks, source=pdf_path)
    print(f"   库中 chunk 数: {collection.count()}")

    # 5. 检索
    print(f"5. 检索: '{query}'")
    docs, metas, scores = search(query)
    print(f"   找到 {len(docs)} 个结果")
    for i, (doc, score) in enumerate(zip(docs, scores)):
        preview = doc[:80].replace("\n", " ")
        print(f"   [{i+1}] 相似度={1 - score:.3f} | {preview}...")


if __name__ == "__main__":
    run_all()
