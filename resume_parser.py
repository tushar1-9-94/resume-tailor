"""
resume_parser.py
Extracts plain text and a lightly-structured view of an uploaded resume
(PDF, DOCX, or TXT) so the rest of the pipeline can work with it.
"""
import os
import re
import docx
import pdfplumber

SECTION_HEADERS = [
    "summary", "professional summary", "objective", "profile",
    "skills", "core competencies", "technical skills",
    "experience", "work experience", "professional experience", "employment history",
    "education", "certifications", "certification", "projects",
    "achievements", "awards", "publications", "languages", "interests",
]


def extract_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return _extract_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return _extract_docx(file_path)
    elif ext == ".txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        raise ValueError(f"Unsupported resume file type: {ext}")


def _extract_pdf(file_path: str) -> str:
    text_chunks = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_chunks.append(page_text)
    return "\n".join(text_chunks)


def _extract_docx(file_path: str) -> str:
    d = docx.Document(file_path)
    parts = []
    for para in d.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in d.tables:
        for row in table.rows:
            for cell in row.cells:
                if cell.text.strip():
                    parts.append(cell.text)
    return "\n".join(parts)


def split_sections(raw_text: str) -> dict:
    """
    Very lightweight section splitter: scans line by line, treats a line that
    matches (case-insensitively, allowing punctuation/whitespace) one of the
    known section headers as a new section boundary.
    """
    lines = [l.strip() for l in raw_text.splitlines()]
    sections = {"header": []}
    current = "header"

    for line in lines:
        if not line:
            continue
        normalized = re.sub(r"[^a-z ]", "", line.lower()).strip()
        matched_header = None
        for header in SECTION_HEADERS:
            if normalized == header or (len(normalized) < 40 and normalized.startswith(header) and len(normalized.split()) <= 4):
                matched_header = header
                break
        if matched_header:
            current = matched_header
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)

    return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}


def extract_contact_info(raw_text: str) -> dict:
    email_match = re.search(r"[\w\.\-+]+@[\w\-]+\.[\w\.\-]+", raw_text)
    phone_match = re.search(r"(\+?\d{1,3}[\s\-]?)?(\(?\d{2,4}\)?[\s\-]?){2,4}\d{3,4}", raw_text)
    linkedin_match = re.search(r"(linkedin\.com/[^\s,]+)", raw_text, re.IGNORECASE)
    name = ""
    for line in raw_text.splitlines():
        stripped = line.strip()
        if stripped and len(stripped.split()) <= 5 and not re.search(r"[@\d]", stripped):
            name = stripped
            break
    return {
        "name": name,
        "email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0).strip() if phone_match else "",
        "linkedin": linkedin_match.group(0) if linkedin_match else "",
    }
