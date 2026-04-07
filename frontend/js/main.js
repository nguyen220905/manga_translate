document.addEventListener("DOMContentLoaded", () => {
  let files = [];
  let lang = "zh";
  let genre = "tu_tien";

  const fileInput = document.getElementById("fileInput");
  const uploadZone = document.getElementById("uploadZone");

  uploadZone.addEventListener("click", e => {
    if (e.target.closest("button")) return;
    fileInput.click();
  });
  const fileListEl = document.getElementById("fileList");
  const errorMsg = document.getElementById("errorMsg");
  const submitBtn = document.getElementById("submitBtn");

  // Selection Logic
  function setupSelection(containerId, callback) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const cards = container.querySelectorAll(".selection-card");
    cards.forEach(card => {
      card.addEventListener("click", () => {
        cards.forEach(c => c.classList.remove("selected"));
        card.classList.add("selected");
        callback(card.dataset.value);
      });
    });
  }

  setupSelection("langOptions", v => lang = v);
  setupSelection("genreOptions", v => genre = v);

  // Drag and drop logic
  uploadZone.addEventListener("dragover", e => {
    e.preventDefault();
    uploadZone.classList.add("dragover");
  });

  uploadZone.addEventListener("dragleave", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
  });

  uploadZone.addEventListener("drop", e => {
    e.preventDefault();
    uploadZone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(Array.from(e.dataTransfer.files));
    }
  });

  fileInput.addEventListener("change", e => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(Array.from(e.target.files));
    }
  });

  function handleFiles(newFiles) {
    files = [...files, ...newFiles];
    renderFiles();
  }

  function renderFiles() {
    fileListEl.innerHTML = "";
    files.forEach((file, idx) => {
      const li = document.createElement("li");
      li.className = "file-chip";
      li.innerHTML = `📄 ${file.name} <span class="remove" data-idx="${idx}">&times;</span>`;
      fileListEl.appendChild(li);
    });

    fileListEl.querySelectorAll(".remove").forEach(btn => {
      btn.addEventListener("click", e => {
        const idx = parseInt(e.target.dataset.idx);
        files.splice(idx, 1);
        renderFiles();
      });
    });
    
    errorMsg.style.display = "none";
  }

  // Submit Logic
  submitBtn.addEventListener("click", async () => {
    if (files.length === 0) {
      errorMsg.textContent = "⚠️ Vui lòng chọn hình ảnh manga để dịch";
      errorMsg.style.display = "block";
      return;
    }

    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span style="animation: pulse-dot 1s infinite">⏳</span> Đang xử lý...`;
    errorMsg.style.display = "none";

    try {
      const job = await createJob(files, lang, genre);
      window.location.href = `/editor.html?id=${job.id}`;
    } catch (err) {
      errorMsg.textContent = `⚠️ ${err.message}`;
      errorMsg.style.display = "block";
      submitBtn.disabled = false;
      submitBtn.innerHTML = `🚀 Dịch Ngay`;
    }
  });
  
});
