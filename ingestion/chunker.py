def chunk_text(text: str, chunk_size=300):#长文本 → [小文本1, 小文本2, ...]
    chunks = []

    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


if __name__ == "__main__":
    from pdf_loader import load_pdf

    text = load_pdf("data/pdfs/test.pdf")
    chunks = chunk_text(text)

    print("chunk数量:", len(chunks))
    print("第一个chunk:", chunks[0])