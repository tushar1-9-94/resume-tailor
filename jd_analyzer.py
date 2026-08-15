"""
jd_analyzer.py
Pulls the important keywords/skills out of a job description and scores
a resume's alignment against them. Pure rule-based / TF-IDF, no external
API required.
"""
import re
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from logger_config import setup_logger

# Set up logger for this module
logger = setup_logger(__name__)

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
    logger.info(f"Starting keyword extraction with top_n={top_n}")
    logger.debug(f"Input JD text length: {len(jd_text)} characters")
    
    jd_text = _clean(jd_text)
    logger.debug(f"Cleaned JD text length: {len(jd_text)} characters")

    seed_hits = {m.group(0).strip().lower() for m in SKILL_SEED_PATTERNS.finditer(jd_text)}
    logger.info(f"Found {len(seed_hits)} seed skill matches: {list(seed_hits)[:10]}...")

    # TF-IDF over sentence-level "documents" so single-JD input still yields
    # a meaningful term ranking.
    sentences = re.split(r"[\.\n•;]", jd_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
    if not sentences:
        sentences = [jd_text]
    
    logger.info(f"Split JD into {len(sentences)} sentences for TF-IDF analysis")

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
        logger.info(f"TF-IDF extracted {len(keywords_ranked)} potential keywords")
        logger.debug(f"Top 10 TF-IDF keywords: {keywords_ranked[:10]}")
    except ValueError as e:
        logger.warning(f"TF-IDF analysis failed: {e}")
        keywords_ranked = []

    ordered = list(seed_hits)
    for kw in keywords_ranked:
        if kw.lower() not in seed_hits and len(ordered) < top_n:
            ordered.append(kw)

    result = ordered[:top_n]
    logger.info(f"Final keyword list: {len(result)} keywords")
    logger.debug(f"Final keywords: {result}")
    return result


def score_resume_against_keywords(resume_text: str, keywords: list) -> dict:
    logger.info("Starting resume keyword scoring")
    logger.debug(f"Resume text length: {len(resume_text)} characters")
    logger.debug(f"Number of keywords to check: {len(keywords)}")
    
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
    
    logger.info(f"Scoring completed: {len(matched)}/{total} keywords matched ({match_pct}%)")
    logger.debug(f"Matched keywords: {matched}")
    logger.debug(f"Missing keywords: {missing}")

    return {
        "matched": matched,
        "missing": missing,
        "match_percentage": match_pct,
        "total_keywords": len(keywords),
    }


def extract_job_title(jd_text: str) -> str:
    logger.info("Starting job title extraction")
    logger.debug(f"Input JD text length: {len(jd_text)} characters")
    
    lines = [l.strip() for l in jd_text.splitlines() if l.strip()]
    if not lines:
        logger.warning("No lines found in JD text")
        return ""
    
    first = lines[0]
    logger.debug(f"First line: {first}")
    
    if len(first.split()) <= 8:
        logger.info(f"Using first line as job title: {first}")
        return first
    
    m = re.search(r"(?:hiring|seeking|looking for)\s+(?:an?\s+)?([A-Z][A-Za-z0-9 \-/]{3,60})", jd_text)
    if m:
        title = m.group(1).strip()
        logger.info(f"Extracted job title from pattern: {title}")
        return title
    
    logger.warning("Could not extract job title from JD")
    return ""
