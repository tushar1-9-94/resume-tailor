const form = document.getElementById("tailorForm");
const submitBtn = document.getElementById("submitBtn");
const statusMsg = document.getElementById("statusMsg");
const fileInput = document.getElementById("resume_file");
const fileLabel = document.getElementById("fileLabel");
const dropzone = document.getElementById("dropzone");
const results = document.getElementById("results");

// Drag and drop functionality
dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => {
  dropzone.classList.remove("dragover");
});

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  
  const files = e.dataTransfer.files;
  if (files.length > 0) {
    fileInput.files = files;
    updateFileLabel();
  }
});

fileInput.addEventListener("change", updateFileLabel);

function updateFileLabel() {
  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];
    fileLabel.textContent = file.name;
    
    // Add file size info
    const sizeKB = (file.size / 1024).toFixed(1);
    const sizeText = file.size < 1024 * 1024 
      ? `${sizeKB} KB` 
      : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
    
    fileLabel.innerHTML = `<strong>${file.name}</strong><br><span style="color: var(--muted); font-size: 13px;">${sizeText}</span>`;
  } else {
    fileLabel.innerHTML = `Drop your resume here or click to browse`;
  }
}

// Form submission with enhanced UX
form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusMsg.className = "";
  statusMsg.textContent = "";

  const jdText = document.getElementById("jd_text").value.trim();
  if (!jdText) {
    statusMsg.className = "error";
    statusMsg.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      Please paste the job description.
    `;
    return;
  }
  if (!fileInput.files.length) {
    statusMsg.className = "error";
    statusMsg.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      Please upload your resume file.
    `;
    return;
  }

  const formData = new FormData();
  formData.append("jd_text", jdText);
  formData.append("resume_file", fileInput.files[0]);

  submitBtn.disabled = true;
  submitBtn.innerHTML = `
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spinner">
      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
    </svg>
    Processing...
  `;
  
  statusMsg.className = "info";
  statusMsg.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"/>
      <polyline points="12 6 12 12 16 14"/>
    </svg>
    Analyzing job description and optimizing your resume...
  `;
  results.classList.add("hidden");

  try {
    const resp = await fetch("/api/tailor", { method: "POST", body: formData });
    const data = await resp.json();

    if (!resp.ok || data.error) {
      statusMsg.className = "error";
      statusMsg.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        ${data.error || "Something went wrong."}
      `;
      return;
    }

    statusMsg.className = "info";
    statusMsg.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      ${data.ai_mode
        ? "Resume optimized with AI-powered rewriting!"
        : "Resume optimized with smart keyword alignment!"}
    `;

    // Animate score numbers
    animateValue("scoreBefore", 0, data.score_before.match_percentage, 1000);
    animateValue("scoreAfter", 0, data.score_after.match_percentage, 1000);

    // Populate matched keywords with animation
    const matchedEl = document.getElementById("matchedKeywords");
    matchedEl.innerHTML = "";
    data.score_after.matched.forEach((kw, index) => {
      const span = document.createElement("span");
      span.textContent = kw;
      span.style.animationDelay = `${index * 50}ms`;
      span.classList.add("chip-animate");
      matchedEl.appendChild(span);
    });
    if (data.score_after.matched.length === 0) {
      matchedEl.innerHTML = '<span style="opacity:0.6">None yet</span>';
    }

    // Populate missing keywords with animation
    const missingEl = document.getElementById("missingKeywords");
    missingEl.innerHTML = "";
    data.score_after.missing.forEach((kw, index) => {
      const span = document.createElement("span");
      span.textContent = kw;
      span.style.animationDelay = `${index * 50}ms`;
      span.classList.add("chip-animate");
      missingEl.appendChild(span);
    });
    if (data.score_after.missing.length === 0) {
      missingEl.innerHTML = '<span style="opacity:0.6">None — full coverage!</span>';
    }

    // Handle notes
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

    // Set download link
    const downloadLink = document.getElementById("downloadLink");
    downloadLink.href = data.download_url;

    // Show results with animation
    results.classList.remove("hidden");
    setTimeout(() => {
      results.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  } catch (err) {
    statusMsg.className = "error";
    statusMsg.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      Network error: ${err.message}
    `;
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
      </svg>
      Optimize My Resume
    `;
  }
});

// Function to animate number values
function animateValue(id, start, end, duration) {
  const obj = document.getElementById(id);
  const range = end - start;
  const startTime = performance.now();
  
  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Easing function for smooth animation
    const easeOutQuart = 1 - Math.pow(1 - progress, 4);
    const current = Math.floor(start + range * easeOutQuart);
    
    obj.textContent = current + "%";
    
    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }
  
  requestAnimationFrame(update);
}

// Add CSS animation for chips
const style = document.createElement('style');
style.textContent = `
  .chip-animate {
    animation: chipFadeIn 0.3s ease forwards;
    opacity: 0;
    transform: translateY(10px);
  }
  
  @keyframes chipFadeIn {
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  .spinner {
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(style);
