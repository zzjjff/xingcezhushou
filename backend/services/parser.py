"""文件解析服务 - 从 Word/PDF 提取文本"""
import os
from docx import Document
import pdfplumber


def parse_docx(file_path: str) -> str:
    """从 Word 文档提取全文"""
    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def parse_pdf(file_path: str) -> str:
    """从 PDF 提取全文"""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def parse_file(file_path: str) -> str:
    """根据文件扩展名选择解析器"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".pdf":
        return parse_pdf(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 .docx 和 .pdf")
