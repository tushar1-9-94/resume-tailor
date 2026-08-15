"""
resume_tailor.py
Produces a JD-aligned, ATS-friendly redesign of a resume.

Two modes:
1. AI mode (if ANTHROPIC_API_KEY is set): sends the parsed resume + JD to
   Claude and asks for a tailored rewrite (summary, skills, and reworded
   experience bullets) that truthfully reflects the candidate's real
   background — no fabricated experience.
2. Fallback rule-based mode: reorders/emphasizes genuinely-matching
   keywords, builds a keyword-optimized summary and skills section from
   content actually present in the resume, and flags gaps instead of
   inventing skills.
"""
import os
import json
import re

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """You are an expert resume writer and ATS (Applicant Tracking System) \
optimization specialist with deep knowledge of how ATS systems parse, score, and rank resumes. \
Your mission is to transform resumes into maximum ATS-compliant documents that align perfectly \
with target job descriptions while maintaining absolute honesty about the candidate's qualifications.

## ATS Optimization Principles You MUST Follow:

### 1. STRUCTURE & FORMATTING (Critical for ATS Parsing)
- Use ONLY standard, ATS-recognized section headers: "Professional Summary", "Core Skills", "Professional Experience", "Education", "Certifications"
- Single-column layout only - NO tables, columns, text boxes, or graphics
- Standard bullet points (• or -) - NO special characters, emojis, or custom symbols
- Simple, clean formatting - NO headers, footers, page numbers, or borders
- Reverse-chronological order for experience and education
- Contact info in plain text at top - NO icons, graphics, or tables
- File format consideration: structure for optimal .docx rendering

### 2. KEYWORD STRATEGY (Maximizing ATS Match Scores)
- Incorporate EXACT keywords and phrases from the job description
- Use keyword variations (acronyms + full terms) when both appear in JD
- Place critical keywords in: professional summary, skills section, and first 3 bullets of relevant experience
- Maintain natural readability - keyword stuffing harms both ATS and human review
- Include action verbs that match JD language (e.g., "led" vs "managed" if JD uses "led")

### 3. CONTENT INTEGRITY (Non-Negotiable)
- NEVER fabricate experience, skills, employers, dates, certifications, or education
- Only rephrase, reorder, emphasize, or quantify what exists in the original resume
- If JD requires something not evidenced in resume, flag it in notes_for_candidate
- No "creative interpretation" - if it's not in the source, it doesn't go in the output

### 4. QUANTIFICATION & IMPACT (ATS + Human Appeal)
- Add numbers, percentages, and metrics where original text supports them
- Use the CAR format: Context, Action, Result
- Emphasize measurable outcomes: "Increased sales by 25%" vs "Improved sales"
- Include scope indicators: "Led team of 12", "Managed $2M budget"

### 5. SKILLS SECTION OPTIMIZATION
- Group skills logically (technical, soft, industry-specific)
- Prioritize skills that match JD requirements
- Use standard industry terminology - avoid obscure or proprietary terms
- Include proficiency levels only if original resume specifies them

### 6. PROFESSIONAL SUMMARY OPTIMIZATION
- Lead with job title target if clear from JD
- Include 3-5 most critical JD keywords naturally
- Highlight unique value proposition based on real experience
- Keep to 3-4 sentences - concise summaries perform better in ATS

### 7. EXPERIENCE BULLET OPTIMIZATION
- Start with strong action verbs matching JD language
- Include at least one quantified result per role when possible
- Order bullets by relevance to target JD
- Use consistent tense (past for past roles, present for current)
- Keep bullets to 1-2 lines - longer bullets can break ATS parsing

### 8. EDUCATION & CERTIFICATIONS
- Use standard degree naming conventions
- Include relevant coursework only if directly related to JD
- List certifications in reverse chronological order
- Include issuing organization and dates when available

## Your Output Requirements:

Return ONLY valid JSON with this exact structure:
{
  "professional_summary": "3-4 sentence ATS-optimized summary incorporating JD keywords and candidate's real value proposition",
  "core_skills": ["skill1", "skill2", ...], // 15-25 skills prioritized by JD relevance, using exact JD terminology when possible
  "experience": [
    {
      "title": "Exact job title from resume",
      "company": "Exact company name from resume", 
      "dates": "Original date format from resume",
      "bullets": ["ATS-optimized, quantified, keyword-aligned bullet points based on real experience", "..."]
    }
  ],
  "education": ["degree, school, year - formatted for ATS parsing", "..."],
  "certifications": ["certification name, issuing organization, year - if available in original", "..."],
  "notes_for_candidate": ["Specific JD requirements not met by current resume, with constructive suggestions for honest addressing", "..."]
}

## Quality Checks Before Output:
- [ ] No fabricated skills, experience, or credentials
- [ ] All keywords supported by original resume content
- [ ] Standard ATS section headers used
- [ ] No tables, columns, or graphics in structure
- [ ] Critical keywords placed in high-visibility sections
- [ ] Quantification added where original text supports it
- [ ] Natural language maintained (no keyword stuffing)
- [ ] Reverse-chronological order followed
- [ ] Consistent formatting throughout

Your goal is to maximize ATS match score while maintaining complete honesty about the candidate's qualifications. Every improvement must be traceable to the original resume content.
"""


def tailor_with_ai(resume_text: str, jd_text: str, contact: dict) -> dict:
    from anthropic import Anthropic

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    user_prompt = f"""JOB DESCRIPTION:
{jd_text}

CANDIDATE'S CURRENT RESUME (raw extracted text):
{resume_text}

Rewrite/restructure this into a JD-aligned, ATS-friendly resume following the required JSON schema. \
Do not invent employers, titles, dates, or skills not evidenced in the original resume. \
Use strong action verbs and quantify impact wherever the original text supports it."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    data = json.loads(raw)
    return data


def tailor_rule_based(resume_text: str, sections: dict, contact: dict,
                       matched_keywords: list, missing_keywords: list, job_title: str) -> dict:
    """Deterministic fallback that never invents content."""
    skills_blob = sections.get("skills", "") or sections.get("core competencies", "") \
        or sections.get("technical skills", "")
    existing_skills = re.split(r"[,\n•;|/]", skills_blob)
    existing_skills = [s.strip() for s in existing_skills if s.strip() and len(s.strip()) < 40]

    # Prioritize skills that also appear in the JD keyword list.
    matched_lower = {k.lower() for k in matched_keywords}
    prioritized = [s for s in existing_skills if s.lower() in matched_lower]
    remaining = [s for s in existing_skills if s.lower() not in matched_lower]
    core_skills = prioritized + remaining
    if not core_skills:
        core_skills = matched_keywords[:12]

    summary_source = sections.get("summary", "") or sections.get("professional summary", "") \
        or sections.get("objective", "") or sections.get("profile", "")
    role_phrase = f"targeting the {job_title} role" if job_title else "aligned to the target role"
    top_kw = ", ".join(matched_keywords[:6]) if matched_keywords else "the role's core requirements"
    if summary_source:
        professional_summary = (
            f"{summary_source.strip()} Experienced professional {role_phrase}, with demonstrated "
            f"strengths in {top_kw}."
        )
    else:
        professional_summary = (
            f"Results-driven professional {role_phrase}, bringing hands-on experience in "
            f"{top_kw}. Proven track record of delivering measurable outcomes and collaborating "
            f"effectively across teams."
        )

    experience_raw = sections.get("experience", "") or sections.get("work experience", "") \
        or sections.get("professional experience", "") or sections.get("employment history", "")
    experience_entries = _parse_experience_blob(experience_raw)

    education_raw = sections.get("education", "")
    education = [l.strip() for l in education_raw.splitlines() if l.strip()]

    certs_raw = sections.get("certifications", "") or sections.get("certification", "")
    certifications = [l.strip() for l in certs_raw.splitlines() if l.strip()]

    notes = []
    if missing_keywords:
        notes.append(
            "The job description emphasizes these terms that weren't clearly found in your resume: "
            + ", ".join(missing_keywords[:12])
            + ". If you have relevant experience with any of these, add specific, honest examples — "
              "do not add skills you don't actually have."
        )

    return {
        "professional_summary": professional_summary,
        "core_skills": core_skills[:20],
        "experience": experience_entries,
        "education": education,
        "certifications": certifications,
        "notes_for_candidate": notes,
    }


def _parse_experience_blob(blob: str) -> list:
    """Best-effort split of a raw experience section into entries+bullets."""
    if not blob.strip():
        return []
    lines = [l.rstrip() for l in blob.splitlines() if l.strip()]
    entries = []
    current = None
    for line in lines:
        is_bullet = bool(re.match(r"^\s*[-•*]", line))
        if is_bullet:
            if current is None:
                current = {"title": "", "company": "", "dates": "", "bullets": []}
                entries.append(current)
            current["bullets"].append(re.sub(r"^\s*[-•*]\s*", "", line))
        else:
            # Treat as a new role header line; pull trailing date range out of
            # the header text so it isn't duplicated in the rendered output.
            date_match = re.search(r"[,\-–—\s]*(\b(?:19|20)\d{2}\b\s*[-–—to]+\s*(?:present|current|\b(?:19|20)\d{2}\b))\s*$", line, re.IGNORECASE)
            if date_match:
                dates = date_match.group(1).strip()
                header = line[:date_match.start()].rstrip(" ,-–—")
            else:
                dates = ""
                header = line
            current = {"title": header, "company": "", "dates": dates, "bullets": []}
            entries.append(current)
    return entries


def tailor_resume(resume_text: str, jd_text: str, sections: dict, contact: dict,
                   matched_keywords: list, missing_keywords: list, job_title: str) -> dict:
    if ANTHROPIC_API_KEY:
        try:
            return tailor_with_ai(resume_text, jd_text, contact)
        except Exception:
            # Fall back silently if the AI call fails for any reason
            pass
    return tailor_rule_based(resume_text, sections, contact, matched_keywords, missing_keywords, job_title)
