const form = document.getElementById("tailorForm");
const submitBtn = document.getElementById("submitBtn");
const statusMsg = document.getElementById("statusMsg");
const fileInput = document.getElementById("resume_file");
const fileLabel = document.getElementById("fileLabel");
const results = document.getElementById("results");

fileInput.addEventListener("change", () => {
  if (fileInput.files.length > 0) {
    fileLabel.textContent = fileInput.files[0].name;
  } else {
    fileLabel.textContent = "Click to choose a file, or drag it here";
  }
});

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusMsg.className = "";
  statusMsg.textContent = "";

  const jdText = document.getElementById("jd_text").value.trim();
  if (!jdText) {
    statusMsg.className = "error";
    statusMsg.textContent = "Please paste the job description.";
    return;
  }
  if (!fileInput.files.length) {
    statusMsg.className = "error";
    statusMsg.textContent = "Please upload your resume file.";
    return;
  }

  const formData = new FormData();
  formData.append("jd_text", jdText);
  formData.append("resume_file", fileInput.files[0]);

  submitBtn.disabled = true;
  statusMsg.className = "info";
  statusMsg.textContent = "Analyzing job description and tailoring your resume...";
  results.classList.add("hidden");

  try {
    const resp = await fetch("/api/tailor", { method: "POST", body: formData });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      statusMsg.className = "error";
      statusMsg.textContent = data.error || "Something went wrong.";
      return;
    }

    statusMsg.className = "info";
    statusMsg.textContent = data.ai_mode
      ? "Done — tailored with AI rewriting."
      : "Done — tailored with rule-based keyword alignment.";

    document.getElementById("scoreBefore").textContent = data.score_before.match_percentage + "%";
    document.getElementById("scoreAfter").textContent = data.score_after.match_percentage + "%";

    const matchedEl = document.getElementById("matchedKeywords");
    matchedEl.innerHTML = "";
    data.score_after.matched.forEach((kw) => {
      const span = document.createElement("span");
      span.textContent = kw;
      matchedEl.appendChild(span);
    });
    if (data.score_after.matched.length === 0) {
      matchedEl.innerHTML = '<span style="opacity:0.6">None yet</span>';
    }

    const missingEl = document.getElementById("missingKeywords");
    missingEl.innerHTML = "";
    data.score_after.missing.forEach((kw) => {
      const span = document.createElement("span");
      span.textContent = kw;
      missingEl.appendChild(span);
    });
    if (data.score_after.missing.length === 0) {
      missingEl.innerHTML = '<span style="opacity:0.6">None — full coverage!</span>';
    }

    const notesBlock = document.getElementById("notesBlock");
    const notesList = document.getElementById("notesList");
    notesList.innerHTML = "";
    if (data.notes_for_candidate && data.notes_for_candidate.length > 0) {
      data.notes_for_candidate.forEach((note) => {
        const li = document.createElement("li");
        li.textContent = note;
        notesList.appendChild(li);
      });
      notesBlock.classList.remove("hidden");
    } else {
      notesBlock.classList.add("hidden");
    }

    const downloadLink = document.getElementById("downloadLink");
    downloadLink.href = data.download_url;

    results.classList.remove("hidden");
    results.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    statusMsg.className = "error";
    statusMsg.textContent = "Network error: " + err.message;
  } finally {
    submitBtn.disabled = false;
  }
});
