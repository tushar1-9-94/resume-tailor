"""
jd_analyzer.py
Pulls the important keywords/skills out of a job description and scores
a resume's alignment against them. Pure rule-based / TF-IDF, no external
API required.
"""
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer

GENERIC_STOPWORDS = {
    "the", "and", "a", "to", "of", "in", "for", "with", "on", "is", "are",
    "as", "at", "by", "an", "be", "or", "will", "you", "we", "our", "your",
    "this", "that", "role", "team", "work", "working", "job", "years",
    "year", "experience", "strong", "ability", "including", "such",
    "etc", "using", "use", "must", "have", "has", "who", "their", "they",
    "it", "its", "about", "into", "across", "within", "other", "all",
    "any", "can", "should", "would", "may", "also", "new", "per",
}

# A reasonably broad seed list of common professional/technical skill terms.
# Any of these found verbatim in the JD are treated as high-confidence
# keywords, in addition to whatever TF-IDF surfaces.
SKILL_SEED_PATTERNS = re.compile(
    r"\b("
    r"python|java|javascript|typescript|react|angular|vue|node\.?js|django|"
    r"flask|spring|sql|nosql|mysql|postgresql|mongodb|redis|kafka|airflow|"
    r"docker|kubernetes|aws|azure|gcp|terraform|ansible|jenkins|ci/cd|git|"
    r"machine learning|deep learning|nlp|computer vision|data science|"
    r"data engineering|data analysis|etl|tableau|power ?bi|excel|spark|"
    r"hadoop|scikit-?learn|tensorflow|pytorch|rest api|graphql|microservices|"
    r"agile|scrum|jira|product management|project management|stakeholder "
    r"management|leadership|communication|problem solving|analytical|"
    r"cross-functional|c\+\+|c#|golang|go|rust|ruby|php|html|css|figma|"
    r"ux|ui design|salesforce|sap|erp|crm|hr|recruiting|marketing|seo|sem|"
    r"content strategy|copywriting|financial modeling|accounting|budgeting|"
    r"forecasting|risk management|compliance|audit|security|cybersecurity|"
    r"network(?:ing)?|linux|bash|shell scripting|api integration|testing|"
    r"qa|quality assurance|automation|selenium|pytest|unit testing|"
    r"cloud computing|devops|mlops"
    r")\b",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_keywords(jd_text: str, top_n: int = 25) -> list:
    jd_text = _clean(jd_text)

    seed_hits = {m.group(0).strip().lower() for m in SKILL_SEED_PATTERNS.finditer(jd_text)}

    # TF-IDF over sentence-level "documents" so single-JD input still yields
    # a meaningful term ranking.
    sentences = re.split(r"[\.\n•;]", jd_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    if not sentences:
        sentences = [jd_text]

    keywords_ranked = []
    try:
        vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words=list(GENERIC_STOPWORDS),
            max_features=200,
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z+#\.\-]{1,}\b",
        )
        matrix = vectorizer.fit_transform(sentences)
        scores = matrix.sum(axis=0).A1
        terms = vectorizer.get_feature_names_out()
        ranked = sorted(zip(terms, scores), key=lambda x: -x[1])
        keywords_ranked = [t for t, s in ranked if t.lower() not in GENERIC_STOPWORDS]
    except ValueError:
        keywords_ranked = []

    ordered = list(seed_hits)
    for kw in keywords_ranked:
        if kw.lower() not in seed_hits and len(ordered) < top_n:
            ordered.append(kw)

    return ordered[:top_n]


def score_resume_against_keywords(resume_text: str, keywords: list) -> dict:
    resume_lower = resume_text.lower()
    matched, missing = [], []
    for kw in keywords:
        pattern = re.escape(kw.lower())
        if re.search(pattern, resume_lower):
            matched.append(kw)
        else:
            missing.append(kw)

    total = len(keywords) or 1
    match_pct = round(100 * len(matched) / total, 1)

    return {
        "matched": matched,
        "missing": missing,
        "match_percentage": match_pct,
        "total_keywords": len(keywords),
    }


def extract_job_title(jd_text: str) -> str:
    lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
    if not lines:
        return ""
    first = lines[0]
    if len(first.split()) <= 8:
        return first
    m = re.search(r"(?:hiring|seeking|looking for)\s+(?:an?\s+)?([A-Z][A-Za-z0-9 \-/]{3,60})", jd_text)
    if m:
        return m.group(1).strip()
    return ""
