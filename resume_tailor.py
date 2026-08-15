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
optimization specialist. You rewrite resumes to align with a specific job description \
WITHOUT fabricating experience, skills, employers, dates, or credentials the candidate \
does not actually have. You may rephrase, reorder, quantify, and emphasize real \
accomplishments to mirror the job description's language and keywords. You always \
produce clean, ATS-friendly structure: no tables, no columns, no graphics, standard \
section headers, and reverse-chronological order.

Return ONLY valid JSON with this exact shape:
{
  "professional_summary": "3-4 sentence summary tailored to the job",
  "core_skills": ["skill1", "skill2", ...],
  "experience": [
    {
      "title": "...",
      "company": "...",
      "dates": "...",
      "bullets": ["Rewritten, quantified, keyword-aligned bullet", "..."]
    }
  ],
  "education": ["degree, school, year", "..."],
  "certifications": ["...", "..."],
  "notes_for_candidate": ["Any JD requirements the resume doesn't currently support, phrased constructively", "..."]
}
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
