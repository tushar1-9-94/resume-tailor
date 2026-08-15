"""
docx_builder.py
Renders the tailored resume data into a clean, ATS-friendly .docx:
single column, no tables/text boxes/images, standard fonts, standard
section headers, reverse-chronological layout.
"""
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn


FONT_NAME = "Calibri"


def _set_font(run, size=11, bold=False, color=None):
    run.font.name = FONT_NAME
    run.font.size = Pt(size)
    run.font.bold = bold
    rFonts = run._element.rPr.rFonts
    rFonts.set(qn("w:eastAsia"), FONT_NAME)
    if color:
        run.font.color.rgb = color


def _add_heading(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text.upper())
    _set_font(run, size=12, bold=True)
    # simple bottom border for a clean section divider
    pPr = p._p.get_or_add_pPr()
    from docx.oxml import OxmlElement
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "444444")
    pBdr.append(bottom)
    pPr.append(pBdr)
    return p


def build_resume_docx(output_path: str, contact: dict, tailored: dict, job_title: str = ""):
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Inches(0.6)
    section.bottom_margin = Inches(0.6)
    section.left_margin = Inches(0.75)
    section.right_margin = Inches(0.75)

    style = doc.styles["Normal"]
    style.font.name = FONT_NAME
    style.font.size = Pt(11)

    # --- Header: name + contact line ---
    name = contact.get("name") or "Your Name"
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(name)
    _set_font(run, size=18, bold=True)

    contact_bits = [b for b in [contact.get("email"), contact.get("phone"), contact.get("linkedin")] if b]
    if contact_bits:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(" | ".join(contact_bits))
        _set_font(run, size=10)

    if job_title:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(f"Target Role: {job_title}")
        _set_font(run, size=10, bold=True)

    # --- Professional Summary ---
    if tailored.get("professional_summary"):
        _add_heading(doc, "Professional Summary")
        p = doc.add_paragraph()
        run = p.add_run(tailored["professional_summary"])
        _set_font(run, size=11)

    # --- Core Skills ---
    skills = tailored.get("core_skills") or []
    if skills:
        _add_heading(doc, "Core Skills")
        # Plain-text comma/pipe separated line (not a table) for max ATS compatibility
        p = doc.add_paragraph()
        run = p.add_run(" | ".join(skills))
        _set_font(run, size=11)

    # --- Experience ---
    experience = tailored.get("experience") or []
    if experience:
        _add_heading(doc, "Professional Experience")
        for entry in experience:
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            title = entry.get("title", "")
            company = entry.get("company", "")
            dates = entry.get("dates", "")
            header_text = title
            if company:
                header_text += f" — {company}" if header_text else company
            run = p.add_run(header_text or "Role")
            _set_font(run, size=11, bold=True)
            if dates:
                run2 = p.add_run(f"\t{dates}")
                _set_font(run2, size=10)
            for bullet in entry.get("bullets", []):
                bp = doc.add_paragraph(style=None)
                bp.paragraph_format.left_indent = Inches(0.25)
                bp.paragraph_format.space_after = Pt(2)
                brun = bp.add_run(f"• {bullet}")
                _set_font(brun, size=11)

    # --- Education ---
    education = tailored.get("education") or []
    if education:
        _add_heading(doc, "Education")
        for line in education:
            p = doc.add_paragraph()
            run = p.add_run(line)
            _set_font(run, size=11)

    # --- Certifications ---
    certifications = tailored.get("certifications") or []
    if certifications:
        _add_heading(doc, "Certifications")
        for line in certifications:
            p = doc.add_paragraph()
            run = p.add_run(line)
            _set_font(run, size=11)

    doc.save(output_path)
    return output_path
