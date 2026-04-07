const API_URL = window.location.origin; // Using the same server as FastAPI mounts this at root

async function createJob(files, sourceLanguage, genre) {
  const formData = new FormData();
  formData.append("source_language", sourceLanguage);
  formData.append("genre", genre);

  files.forEach(file => formData.append("files", file));

  const res = await fetch(`${API_URL}/api/jobs`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed: ${res.statusText}`);
  }
  return res.json();
}

async function getJob(jobId) {
  const res = await fetch(`${API_URL}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.statusText}`);
  return res.json();
}

async function updateBubble(bubbleId, updateData) {
  const res = await fetch(`${API_URL}/api/bubbles/${bubbleId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updateData),
  });
  if (!res.ok) throw new Error(`Failed to update bubble: ${res.statusText}`);
  return res.json();
}

function getImageUrl(filename) {
  return `${API_URL}/api/images/${filename}`;
}

