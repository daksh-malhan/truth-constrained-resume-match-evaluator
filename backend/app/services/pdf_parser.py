from __future__ import annotations

import re
from typing import List

from ..schemas import ResumeSection

SECTION_NAMES = [
    "summary", "skills", "work experience", "experience", "projects", "education", "certifications",
    "achievements", "other",
]


def _extract_pages(pdf_bytes: bytes) -> List[str]:
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return [page.get_text("text") for page in doc]
    except Exception:
        text = pdf_bytes.decode("utf-8", errors="ignore")
        return [text] if text.strip() else []


def validate_pdf(filename: str, content_type: str | None, pdf_bytes: bytes, max_bytes: int) -> None:
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Only PDF uploads are accepted")
    if len(pdf_bytes) > max_bytes:
        raise ValueError("PDF exceeds configured size limit")
    if not pdf_bytes.startswith(b"%PDF"):
        raise ValueError("Uploaded file does not look like a PDF")


def parse_resume_pdf(pdf_bytes: bytes) -> List[ResumeSection]:
    pages = _extract_pages(pdf_bytes)
    sections: List[ResumeSection] = []
    counter = 0
    for page_number, page_text in enumerate(pages, start=1):
        text = re.sub(r"\n{3,}", "\n\n", page_text).strip()
        if not text:
            continue
        current_name = "Other"
        current_lines: List[str] = []
        for line in text.splitlines():
            normalized = line.strip().lower().rstrip(":")
            if normalized in SECTION_NAMES or normalized in {"professional summary", "technical skills"}:
                if current_lines:
                    body = "\n".join(current_lines).strip()
                    sections.append(
                        ResumeSection(
                            id=f"resume_section_{counter:03d}",
                            section_name=current_name,
                            text=body,
                            page_number=page_number,
                            source_quote=body[:300],
                            confidence=0.75,
                        )
                    )
                    counter += 1
                    current_lines = []
                current_name = "Skills" if "skill" in normalized else normalized.title()
            else:
                current_lines.append(line)
        if current_lines:
            body = "\n".join(current_lines).strip()
            sections.append(
                ResumeSection(
                    id=f"resume_section_{counter:03d}",
                    section_name=current_name,
                    text=body,
                    page_number=page_number,
                    source_quote=body[:300],
                    confidence=0.7 if current_name == "Other" else 0.85,
                )
            )
            counter += 1
    if not sections and pages:
        body = "\n".join(pages).strip()
        sections.append(ResumeSection(id="resume_section_000", section_name="Other", text=body, page_number=1, source_quote=body[:300], confidence=0.5))
    return sections

