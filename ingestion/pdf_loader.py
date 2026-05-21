from pypdf import PdfReader

#文件 → 字符串
def load_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)

    text_list = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_list.append(text)

    return "\n".join(text_list)