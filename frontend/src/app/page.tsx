"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { createJob } from "@/lib/api";
import UploadZone from "@/components/UploadZone";
import GenrePicker from "@/components/GenrePicker";

const LANGUAGES = [
  { code: "zh", label: "🇨🇳 Trung Quốc", flag: "🇨🇳" },
  { code: "ja", label: "🇯🇵 Nhật Bản", flag: "🇯🇵" },
  { code: "ko", label: "🇰🇷 Hàn Quốc", flag: "🇰🇷" },
  { code: "en", label: "🇬🇧 Tiếng Anh", flag: "🇬🇧" },
];

export default function HomePage() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [lang, setLang] = useState("zh");
  const [genre, setGenre] = useState("tu_tien");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = useCallback(async () => {
    if (files.length === 0) {
      setError("Vui lòng chọn hình ảnh manga để dịch");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const job = await createJob(files, lang, genre);
      router.push(`/editor/${job.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Có lỗi xảy ra");
    } finally {
      setLoading(false);
    }
  }, [files, lang, genre, router]);

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="page-wrapper">
      {/* ── Header ──────────────────────────── */}
      <header style={{
        padding: "20px 0",
        borderBottom: "1px solid var(--border-subtle)",
      }}>
        <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "1.8rem" }}>🎌</span>
            <div>
              <h1 style={{
                fontSize: "1.4rem",
                fontWeight: 800,
                background: "var(--gradient-primary)",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                lineHeight: 1.2,
              }}>
                MangaDich
              </h1>
              <p style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontWeight: 500 }}>
                AI Manga Translation
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* ── Hero ────────────────────────────── */}
      <main className="container" style={{ flex: 1, paddingTop: "48px", paddingBottom: "48px" }}>
        <div className="animate-in" style={{ textAlign: "center", marginBottom: "48px" }}>
          <h2 style={{
            fontSize: "2.8rem",
            fontWeight: 900,
            lineHeight: 1.2,
            marginBottom: "16px",
            background: "linear-gradient(135deg, #f0f0f5 0%, #9ca3af 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}>
            Dịch Manga Tự Động
          </h2>
          <p style={{
            fontSize: "1.15rem",
            color: "var(--text-secondary)",
            maxWidth: "580px",
            margin: "0 auto",
            lineHeight: 1.7,
          }}>
            Upload trang manga → AI sẽ <strong style={{ color: "var(--accent-purple)" }}>nhận diện chữ</strong>,{" "}
            <strong style={{ color: "var(--accent-blue)" }}>xóa text gốc</strong>,{" "}
            <strong style={{ color: "var(--accent-cyan)" }}>dịch sang tiếng Việt</strong>{" "}
            và ghép lại hoàn hảo trên ảnh gốc.
          </p>
        </div>

        {/* ── Upload Zone ───────────────────── */}
        <div className="animate-in animate-in-delay-1" style={{ marginBottom: "32px" }}>
          <UploadZone files={files} onFilesChange={setFiles} />
        </div>

        {/* ── File List ─────────────────────── */}
        {files.length > 0 && (
          <div className="animate-in" style={{ marginBottom: "32px" }}>
            <ul className="file-list">
              {files.map((file, i) => (
                <li key={i} className="file-chip">
                  📄 {file.name}
                  <span className="remove" onClick={() => removeFile(i)}>×</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* ── Language Selector ─────────────── */}
        <div className="animate-in animate-in-delay-2" style={{ marginBottom: "32px" }}>
          <p className="section-title">Ngôn ngữ gốc</p>
          <div className="lang-grid">
            {LANGUAGES.map((l) => (
              <button
                key={l.code}
                className={`lang-btn ${lang === l.code ? "selected" : ""}`}
                onClick={() => setLang(l.code)}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Genre Picker ──────────────────── */}
        <div className="animate-in animate-in-delay-3" style={{ marginBottom: "40px" }}>
          <p className="section-title">Thể loại</p>
          <GenrePicker selected={genre} onSelect={setGenre} />
        </div>

        {/* ── Error Message ─────────────────── */}
        {error && (
          <div style={{
            padding: "12px 16px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: "var(--radius-sm)",
            color: "#f87171",
            fontSize: "0.9rem",
            marginBottom: "20px",
          }}>
            ⚠️ {error}
          </div>
        )}

        {/* ── Submit Button ─────────────────── */}
        <div className="animate-in animate-in-delay-4" style={{ textAlign: "center" }}>
          <button
            className="btn btn-primary"
            onClick={handleUpload}
            disabled={loading || files.length === 0}
            style={{
              fontSize: "1.1rem",
              padding: "16px 48px",
              borderRadius: "var(--radius-xl)",
            }}
          >
            {loading ? (
              <>
                <span style={{ animation: "pulse-dot 1s infinite" }}>⏳</span>
                Đang xử lý...
              </>
            ) : (
              <>🚀 Dịch Ngay</>
            )}
          </button>
        </div>
      </main>

      {/* ── Footer ──────────────────────────── */}
      <footer style={{
        padding: "20px 0",
        borderTop: "1px solid var(--border-subtle)",
        textAlign: "center",
      }}>
        <p style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          MangaDich — Powered by AI · OCR · Inpainting · Gemini Flash
        </p>
      </footer>
    </div>
  );
}
