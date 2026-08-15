import os
import uuid
from flask import Flask, request, render_template, send_file, jsonify
from werkzeug.utils import secure_filename

from resume_parser import extract_text, split_sections, extract_contact_info
from jd_analyzer import extract_keywords, score_resume_against_keywords, extract_job_title
from resume_tailor import tailor_resume
from docx_builder import build_resume_docx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt"}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "0") == "1"


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    ai_enabled = bool(os.environ.get("ANTHROPIC_API_KEY"))
    return render_template("index.html", ai_enabled=ai_enabled, debug=app.debug)


@app.route("/api/tailor", methods=["POST"])
def tailor():
    jd_text = request.form.get("jd_text", "").strip()
    resume_file = request.files.get("resume_file")

    if not jd_text:
        return jsonify({"error": "Please paste the job description."}), 400
    if not resume_file or resume_file.filename == "":
        return jsonify({"error": "Please upload a resume file."}), 400
    if not allowed_file(resume_file.filename):
        return jsonify({"error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400

    run_id = uuid.uuid4().hex[:12]
    safe_name = secure_filename(resume_file.filename)
    upload_path = os.path.join(UPLOAD_DIR, f"{run_id}_{safe_name}")
    resume_file.save(upload_path)

    try:
        resume_text = extract_text(upload_path)
        if not resume_text.strip():
            return jsonify({"error": "Could not extract any text from that resume file."}), 400

        sections = split_sections(resume_text)
        contact = extract_contact_info(resume_text)
        job_title = extract_job_title(jd_text)

        keywords = extract_keywords(jd_text, top_n=25)
        score_before = score_resume_against_keywords(resume_text, keywords)

        tailored = tailor_resume(
            resume_text=resume_text,
            jd_text=jd_text,
            sections=sections,
            contact=contact,
            matched_keywords=score_before["matched"],
            missing_keywords=score_before["missing"],
            job_title=job_title,
        )

        output_filename = f"tailored_resume_{run_id}.docx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        build_resume_docx(output_path, contact, tailored, job_title)

        # Re-score against the tailored output text for an "after" number
        tailored_flat_text = " ".join([
            tailored.get("professional_summary", ""),
            " ".join(tailored.get("core_skills", [])),
            " ".join(
                b for e in tailored.get("experience", []) for b in e.get("bullets", [])
            ),
        ])
        score_after = score_resume_against_keywords(tailored_flat_text, keywords)

        return jsonify({
            "success": True,
            "download_url": f"/api/download/{output_filename}",
            "job_title": job_title,
            "keywords": keywords,
            "score_before": score_before,
            "score_after": score_after,
            "notes_for_candidate": tailored.get("notes_for_candidate", []),
            "ai_mode": bool(os.environ.get("ANTHROPIC_API_KEY")),
        })
    except Exception as exc:
        return jsonify({"error": f"Something went wrong while processing: {exc}"}), 500
    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


@app.route("/api/download/<path:filename>")
def download(filename):
    safe_name = secure_filename(filename)
    file_path = os.path.join(OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found."}), 404
    return send_file(
        file_path,
        as_attachment=True,
        download_name="tailored_resume.docx",
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
