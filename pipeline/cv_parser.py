"""
BioCred Pipeline — Step 2: CV Parser
Extracts structured sections from CV files (PDF, DOCX, TXT).
Output: parsed_cv dict with header info, sections, and raw text.
Handles combined headers, PDF artifacts, and diverse CV formats.
No interpretation — just structure extraction.
"""

import json
import re
import sys
from pathlib import Path

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


SECTION_PATTERNS = [
    ("employment", [
        r"(?i)(professional\s+)?experience",
        r"(?i)employment(\s+history)?",
        r"(?i)work\s+(history|experience)",
        r"(?i)career\s+(history|summary)",
        r"(?i)positions?\s+held",
        r"(?i)relevant\s+experience",
    ]),
    ("education", [
        r"(?i)education(al)?\s*(background|history)?",
        r"(?i)academic\s+(background|qualifications|training)",
        r"(?i)degrees?(\s+earned)?",
    ]),
    ("certifications", [
        r"(?i)certifications?(\s+and\s+licenses?)?",
        r"(?i)licenses?(\s+and\s+certifications?)?",
        r"(?i)permits?(\s+and\s+authorizations?)?",
        r"(?i)professional\s+(certifications?|licenses?)",
        r"(?i)authorizations?",
        r"(?i)accreditations?",
    ]),
    ("publications", [
        r"(?i)publications?",
        r"(?i)peer[\s-]?reviewed",
        r"(?i)selected\s+publications?",
        r"(?i)reports?\s+and\s+publications?",
        r"(?i)technical\s+reports?",
        r"(?i)presentations?\s+and\s+publications?",
    ]),
    ("skills", [
        r"(?i)(technical\s+)?skills?",
        r"(?i)tools?\s+and\s+(techniques?|methods?)",
        r"(?i)competenc(ies|y)",
        r"(?i)software(\s+and\s+tools)?",
        r"(?i)methods?(\s+and\s+techniques?)?",
        r"(?i)areas?\s+of\s+expertise",
        r"(?i)core\s+competenc",
        r"(?i)proficienc(ies|y)",
    ]),
    ("projects", [
        r"(?i)(selected\s+)?projects?",
        r"(?i)project\s+experience",
        r"(?i)notable\s+projects?",
    ]),
    ("affiliations", [
        r"(?i)(professional\s+)?affiliations?",
        r"(?i)memberships?",
        r"(?i)professional\s+organizations?",
    ]),
]

COMBINED_HEADER_MAP = {
    r"(?i)education\s+and\s+certifications?": ("education", "certifications"),
    r"(?i)certifications?\s+and\s+education": ("certifications", "education"),
    r"(?i)licenses?\s+and\s+permits?": ("certifications", "certifications"),
    r"(?i)permits?\s+and\s+licenses?": ("certifications", "certifications"),
    r"(?i)skills?\s+and\s+tools?": ("skills", "skills"),
    r"(?i)publications?\s+and\s+presentations?": ("publications", "publications"),
}

PAGE_ARTIFACT_PATTERNS = [
    re.compile(r"^\s*page\s+\d+\s*(of\s+\d+)?\s*$", re.IGNORECASE),
    re.compile(r"^\s*-\s*\d+\s*-\s*$"),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*(confidential|curriculum\s+vitae|resume)\s*$", re.I),
]

BULLET_LIKE = re.compile(r"^\s*[-•▪◦*→‣]\s+|^\s*\d+[.)]\s+")

EMAIL_PATTERN = re.compile(r"[\w.-]+@[\w.-]+\.\w+")
PHONE_PATTERN = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
LOCATION_PATTERN = re.compile(
    r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*),\s*([A-Z]{2})\b"
)


def extract_text_from_pdf(file_path: str) -> str:
    if PdfReader is None:
        raise ImportError("PyPDF2 required: pip install PyPDF2")
    reader = PdfReader(file_path)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def extract_text_from_docx(file_path: str) -> str:
    if DocxDocument is None:
        raise ImportError("python-docx required: pip install python-docx")
    doc = DocxDocument(file_path)
    return "\n".join(p.text for p in doc.paragraphs)


def extract_text_from_txt(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    ext = path.suffix.lower()
    extractors = {
        ".pdf": extract_text_from_pdf,
        ".docx": extract_text_from_docx,
        ".txt": extract_text_from_txt,
        ".text": extract_text_from_txt,
    }
    extractor = extractors.get(ext)
    if not extractor:
        raise ValueError(f"Unsupported file type: {ext}")
    return extractor(file_path)


def clean_text(text: str) -> str:
    """Remove common PDF artifacts (page numbers, headers/footers)."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if any(p.match(line) for p in PAGE_ARTIFACT_PATTERNS):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_header_info(text: str) -> dict:
    """Extract name, email, phone, location from CV header area."""
    lines = text.split("\n")
    header_lines = lines[:8]
    header_text = "\n".join(header_lines)

    name = ""
    for line in header_lines[:3]:
        stripped = line.strip()
        if not stripped:
            continue
        if EMAIL_PATTERN.search(stripped) or PHONE_PATTERN.search(stripped):
            continue
        if len(stripped) > 5 and not re.search(r"\d{4}", stripped):
            name = stripped.rstrip(",").strip()
            break

    email_match = EMAIL_PATTERN.search(header_text)
    phone_match = PHONE_PATTERN.search(header_text)
    location_match = LOCATION_PATTERN.search(header_text)

    return {
        "name": name,
        "email": email_match.group() if email_match else "",
        "phone": phone_match.group() if phone_match else "",
        "location": location_match.group() if location_match else "",
    }


def resolve_combined_header(header_text: str) -> str:
    """Check if a header is a combined section like 'Education and Certs'."""
    for pattern, (primary, _) in COMBINED_HEADER_MAP.items():
        if re.search(pattern, header_text):
            return primary
    return None


def find_section_boundaries(text: str) -> list:
    lines = text.split("\n")
    boundaries = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 80:
            continue
        if stripped.endswith(".") and len(stripped) > 40:
            continue
        if BULLET_LIKE.match(stripped):
            continue

        combined = resolve_combined_header(stripped)
        if combined:
            boundaries.append({
                "section": combined,
                "line_index": i,
                "header_text": stripped,
            })
            continue

        for section_name, patterns in SECTION_PATTERNS:
            for pattern in patterns:
                if re.search(pattern, stripped):
                    boundaries.append({
                        "section": section_name,
                        "line_index": i,
                        "header_text": stripped,
                    })
                    break
            else:
                continue
            break

    boundaries.sort(key=lambda b: b["line_index"])
    return boundaries


def split_into_sections(text: str) -> dict:
    lines = text.split("\n")
    boundaries = find_section_boundaries(text)
    sections = {}

    for idx, boundary in enumerate(boundaries):
        start = boundary["line_index"] + 1
        if idx + 1 < len(boundaries):
            end = boundaries[idx + 1]["line_index"]
        else:
            end = len(lines)

        content = "\n".join(lines[start:end]).strip()
        section_name = boundary["section"]

        if section_name in sections:
            sections[section_name] += "\n\n" + content
        else:
            sections[section_name] = content

    if not sections:
        sections["unclassified"] = text.strip()

    return sections


def parse_cv(file_path: str) -> dict:
    raw_text = extract_text(file_path)
    text = clean_text(raw_text)
    header = extract_header_info(text)
    sections = split_into_sections(text)

    return {
        "source_file": Path(file_path).name,
        "total_characters": len(text),
        "total_lines": len(text.split("\n")),
        "header": header,
        "sections_found": list(sections.keys()),
        "sections": sections,
        "raw_text": text,
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python cv_parser.py <cv_file> [output.json]")
        print("Supported: .pdf, .docx, .txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "parsed_cv.json"

    result = parse_cv(input_file)

    Path(output_file).write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"Parsed: {input_file}")
    print(f"Header: {result['header']}")
    print(f"Sections found: {result['sections_found']}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
