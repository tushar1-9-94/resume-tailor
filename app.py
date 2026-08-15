import os
import uuid
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

from logger_config import setup_logger
from resume_parser import extract_text, split_sections, extract_contact_info
from jd_analyzer import extract_keywords, score_resume_against_keywords, extract_job_title
from resume_tailor import tailor_resume
from docx_builder import build_resume_docx

# Set up logger for this module
logger = setup_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

logger.info(f"Upload directory: {UPLOAD_DIR}")
logger.info(f"Output directory: {OUTPUT_DIR}")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "0") == "1"

logger.info(f"Flask app configured with MAX_CONTENT_LENGTH: {app.config['MAX_CONTENT_LENGTH']} bytes")
logger.info(f"Debug mode: {app.config['DEBUG']}")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _format_experience_suggestions(experience_data):
    """Format experience suggestions for display"""
    if not experience_data:
        return ""
    
    formatted = []
    for entry in experience_data:
        title = entry.get("title", "")
        company = entry.get("company", "")
        dates = entry.get("dates", "")
        bullets = entry.get("bullets", [])
        
        entry_text = f"{title}"
        if company:
            entry_text += f" | {company}"
        if dates:
            entry_text += f" | {dates}"
        
        formatted.append(entry_text)
        for bullet in bullets:
            formatted.append(f"• {bullet}")
        formatted.append("")  # Empty line between entries
    
    return "\n".join(formatted)


@app.route("/")
def index():
    logger.info("Index route accessed")
    ai_enabled = bool(os.environ.get("ANTHROPIC_API_KEY"))
    logger.info(f"AI mode enabled: {ai_enabled}")
    return render_template("index.html", ai_enabled=ai_enabled, debug=app.debug)


@app.route("/api/tailor", methods=["POST"])
def tailor():
    logger.info("=== Starting resume tailoring process ===")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request content type: {request.content_type}")
    
    jd_text = request.form.get("jd_text", "").strip()
    resume_file = request.files.get("resume_file")

    logger.info(f"Job description length: {len(jd_text)} characters")
    logger.info(f"Resume file provided: {resume_file is not None}")
    
    if resume_file:
        logger.info(f"Resume filename: {resume_file.filename}")
        logger.info(f"Resume file size: {resume_file.content_length} bytes")

    if not jd_text:
        logger.warning("Job description is empty")
        return jsonify({"error": "Please paste the job description."}), 400
    if not resume_file or resume_file.filename == "":
        logger.warning("No resume file uploaded")
        return jsonify({"error": "Please upload a resume file."}), 400
    if not allowed_file(resume_file.filename):
        logger.warning(f"Invalid file type: {resume_file.filename}")
        return jsonify({"error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400

    run_id = uuid.uuid4().hex[:12]
    safe_name = secure_filename(resume_file.filename)
    upload_path = os.path.join(UPLOAD_DIR, f"{run_id}_{safe_name}")
    
    logger.info(f"Generated run ID: {run_id}")
    logger.info(f"Safe filename: {safe_name}")
    logger.info(f"Upload path: {upload_path}")
    
    resume_file.save(upload_path)
    logger.info(f"File saved successfully to {upload_path}")

    try:
        logger.info("Starting text extraction from resume")
        resume_text = extract_text(upload_path)
        logger.info(f"Extracted text length: {len(resume_text)} characters")
        
        if not resume_text.strip():
            logger.error("No text could be extracted from resume file")
            return jsonify({"error": "Could not extract any text from that resume file."}), 400

        logger.info("Starting resume section parsing")
        sections = split_sections(resume_text)
        logger.info(f"Parsed sections: {list(sections.keys())}")
        
        logger.info("Extracting contact information")
        contact = extract_contact_info(resume_text)
        logger.info(f"Contact info extracted: {contact}")
        
        logger.info("Extracting job title from JD")
        job_title = extract_job_title(jd_text)
        logger.info(f"Extracted job title: {job_title}")

        logger.info("Extracting keywords from job description")
        keywords = extract_keywords(jd_text, top_n=25)
        logger.info(f"Extracted {len(keywords)} keywords: {keywords[:5]}...")  # Log first 5
        
        logger.info("Scoring original resume against keywords")
        score_before = score_resume_against_keywords(resume_text, keywords)
        logger.info(f"Original resume score: {score_before['match_percentage']}%")
        logger.info(f"Matched keywords: {len(score_before['matched'])}")
        logger.info(f"Missing keywords: {len(score_before['missing'])}")

        logger.info("Starting resume tailoring process")
        tailored = tailor_resume(
            resume_text=resume_text,
            jd_text=jd_text,
            sections=sections,
            contact=contact,
            matched_keywords=score_before["matched"],
            missing_keywords=score_before["missing"],
            job_title=job_title,
        )
        logger.info("Resume tailoring completed")
        logger.info(f"Tailored sections: {list(tailored.keys())}")

        # Re-score against the tailored output text for an "after" number
        logger.info("Re-scoring tailored resume against keywords")
        tailored_flat_text = " ".join([
            tailored.get("professional_summary", ""),
            " ".join(tailored.get("core_skills", [])),
            " ".join(
                b for e in tailored.get("experience", []) for b in e.get("bullets", [])
            ),
        ])
        logger.info(f"Tailored text length for scoring: {len(tailored_flat_text)} characters")
        
        score_after = score_resume_against_keywords(tailored_flat_text, keywords)
        logger.info(f"Tailored resume score: {score_after['match_percentage']}%")
        logger.info(f"Improvement: {score_after['match_percentage'] - score_before['match_percentage']}%")

        ai_mode = bool(os.environ.get("ANTHROPIC_API_KEY"))
        logger.info(f"AI mode used: {ai_mode}")

        # Prepare section-by-section suggestions with original content
        section_suggestions = {
            "professional_summary": {
                "original": sections.get("summary", "") or sections.get("professional summary", "") or sections.get("objective", "") or sections.get("profile", ""),
                "suggested": tailored.get("professional_summary", ""),
                "reasoning": "Optimized to include key JD keywords and highlight relevant experience for the target role."
            },
            "core_skills": {
                "original": sections.get("skills", "") or sections.get("core competencies", "") or sections.get("technical skills", ""),
                "suggested": " | ".join(tailored.get("core_skills", [])),
                "reasoning": "Prioritized skills that match the JD requirements, reordered for maximum ATS keyword matching."
            },
            "experience": {
                "original": sections.get("experience", "") or sections.get("work experience", "") or sections.get("professional experience", ""),
                "suggested": _format_experience_suggestions(tailored.get("experience", [])),
                "reasoning": "Enhanced bullet points with stronger action verbs, quantification, and JD-specific keywords while maintaining your actual experience."
            },
            "education": {
                "original": sections.get("education", ""),
                "suggested": "\n".join(tailored.get("education", [])),
                "reasoning": "Formatted for consistency and clarity, no changes to actual credentials."
            },
            "certifications": {
                "original": sections.get("certifications", "") or sections.get("certification", ""),
                "suggested": "\n".join(tailored.get("certifications", [])),
                "reasoning": "Standardized formatting for better ATS parsing."
            }
        }

        response_data = {
            "success": True,
            "job_title": job_title,
            "keywords": keywords,
            "score_before": score_before,
            "score_after": score_after,
            "notes_for_candidate": tailored.get("notes_for_candidate", []),
            "ai_mode": ai_mode,
            "contact": contact,
            "section_suggestions": section_suggestions,
            "tailored_content": tailored
        }
        logger.info("=== Resume tailoring process completed successfully ===")
        return jsonify(response_data)
    except Exception as exc:
        logger.error(f"Error during resume tailoring: {exc}", exc_info=True)
        return jsonify({"error": f"Something went wrong while processing: {exc}"}), 500
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)
            logger.info(f"Cleaned up upload file: {upload_path}")


@app.route("/api/download/<path:filename>")
def download(filename):
    logger.info(f"Download request for file: {filename}")
    safe_name = secure_filename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    logger.info(f"Safe filename: {safe_name}")
    logger.info(f"File path: {file_path}")
    
    if not os.path.exists(file_path):
        logger.warning(f"File not found: {file_path}")
        return jsonify({"error": "File not found."}), 404
    
    logger.info(f"File exists, serving download: {file_path}")
    return send_file(
        file_path,
        as_attachment=True,
        download_name="tailored_resume.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    
    logger.info("=" * 50)
    logger.info("Starting ATS Resume Tailor Application")
    logger.info("=" * 50)
    logger.info(f"Port: {port}")
    logger.info(f"Debug mode: {debug}")
    logger.info(f"AI mode enabled: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
    logger.info(f"Log level: {os.environ.get('LOG_LEVEL', 'INFO')}")
    logger.info("=" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=debug)
