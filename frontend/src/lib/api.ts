const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Bubble {
  id: number;
  page_id: number;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  ocr_text: string | null;
  translated_text: string | null;
  edited_text: string | null;
  font_size: number;
  confidence: number;
}

export interface Page {
  id: number;
  job_id: number;
  page_number: number;
  original_image_url: string;
  inpainted_image_url: string | null;
  width: number | null;
  height: number | null;
  bubbles: Bubble[];
}

export interface Job {
  id: number;
  status: string;
  source_language: string;
  genre: string;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
  processing_started_at: string | null;
  ocr_seconds: number | null;
  inpaint_seconds: number | null;
  translate_seconds: number | null;
  total_seconds: number | null;
  pages: Page[];
}

export interface JobListItem {
  id: number;
  status: string;
  source_language: string;
  genre: string;
  created_at: string;
  page_count: number;
}

// ── Create Job ─────────────────────────────────────────
export async function createJob(
  files: File[],
  sourceLanguage: string,
  genre: string
): Promise<Job> {
  const formData = new FormData();
  formData.append("source_language", sourceLanguage);
  formData.append("genre", genre);
  files.forEach((file) => formData.append("files", file));

  const res = await fetch(`${API_URL}/api/jobs`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
}

// ── Get Job ────────────────────────────────────────────
export async function getJob(jobId: number): Promise<Job> {
  const res = await fetch(`${API_URL}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job: ${res.statusText}`);
  return res.json();
}

// ── List Jobs ──────────────────────────────────────────
export async function listJobs(): Promise<JobListItem[]> {
  const res = await fetch(`${API_URL}/api/jobs`);
  if (!res.ok) throw new Error(`Failed to list jobs: ${res.statusText}`);
  return res.json();
}

// ── Update Bubble ──────────────────────────────────────
export async function updateBubble(
  bubbleId: number,
  update: Partial<Bubble>
): Promise<Bubble> {
  const res = await fetch(`${API_URL}/api/bubbles/${bubbleId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!res.ok) throw new Error(`Failed to update bubble: ${res.statusText}`);
  return res.json();
}

// ── Image URL helper ───────────────────────────────────
export function getImageUrl(filename: string): string {
  return `${API_URL}/api/images/${filename}`;
}
