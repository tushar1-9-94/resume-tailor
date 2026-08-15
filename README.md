# ATS Resume Tailor

A small web app that takes a job description and your existing resume, and produces a redesigned, **ATS-friendly**, **JD-aligned** version you can download as a `.docx`.

## What it does

1. Paste a job description and upload your resume (PDF, DOCX, or TXT).
2. The app extracts the JD's key skills/requirements (TF-IDF + a curated skills dictionary).
3. It scores your current resume against those keywords ("before" score).
4. It rewrites/restructures your resume:
   - **With an `ANTHROPIC_API_KEY` set**, it uses Claude to rewrite your summary, skills, and experience bullets so they genuinely mirror the JD's language — without inventing employers, titles, or skills you don't have.
   - **Without a key**, it falls back to a deterministic, rule-based tailoring: it reorders/prioritizes your real skills that match the JD, builds a keyword-aware summary from your existing content, and leaves your experience bullets as-is.
5. It renders the result into a clean, single-column `.docx` using standard section headers (Professional Summary, Core Skills, Professional Experience, Education, Certifications) — no tables, columns, text boxes, or images, which is what trips up most ATS parsers.
6. It shows you a "before vs. after" keyword match score, plus an honest list of JD requirements your resume still doesn't support, so you can decide whether to address them yourself (the app will never fabricate experience).

## Setup

```bash
cd resume-tailor
pip install -r requirements.txt
```

Optional — enable AI-powered rewriting:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Run

```bash
python3 app.py
```

Then open http://localhost:5000 in your browser.

## Project structure

```
app.py              Flask routes (UI + /api/tailor + /api/download)
resume_parser.py     Extracts text/sections/contact info from PDF/DOCX/TXT resumes
jd_analyzer.py        Extracts JD keywords and scores resume/JD alignment
resume_tailor.py      Produces the tailored resume content (AI or rule-based)
docx_builder.py        Renders the tailored content into an ATS-friendly .docx
templates/index.html  UI
static/style.css       UI styling
static/app.js           UI logic (fetch, render results)
```

## Notes on ATS-friendliness

The generated resume deliberately avoids the formatting choices that most commonly break ATS parsers:
- Single column, no tables or text boxes
- No headers/footers, no images/icons for contact info
- Standard, commonly-recognized section headings
- Reverse-chronological experience with plain bullet characters
- A plain-text "Core Skills" line (pipe-separated) rather than a skills graphic or table

## Honesty guardrail

Neither the AI prompt nor the rule-based fallback invents skills, employers, titles, or dates. Where the JD asks for something your resume doesn't support, the app surfaces it as a note so you can decide whether/how to address it truthfully — it will not silently add it to your resume.
