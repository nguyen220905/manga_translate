"use client";

import { useEffect, useState, useCallback, useRef, use } from "react";
import { getJob, type Job, type Bubble, updateBubble } from "@/lib/api";
import CanvasEditor from "@/components/CanvasEditor";
import JobStatusComponent from "@/components/JobStatus";

interface EditorPageProps {
    params: Promise<{ jobId: string }>;
}

function LiveTimer({ startTime }: { startTime: string | null }) {
    const [elapsed, setElapsed] = useState(0);

    useEffect(() => {
        if (!startTime) return;
        const start = new Date(startTime).getTime();

        const tick = () => {
            setElapsed((Date.now() - start) / 1000);
        };
        tick();
        const id = setInterval(tick, 100);
        return () => clearInterval(id);
    }, [startTime]);

    if (!startTime) return null;

    const mins = Math.floor(elapsed / 60);
    const secs = (elapsed % 60).toFixed(1);

    return (
        <span style={{
            fontFamily: "'Courier New', monospace",
            fontSize: "1.6rem",
            fontWeight: 800,
            background: "var(--gradient-primary)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
        }}>
            {mins > 0 ? `${mins}m ` : ""}{secs}s
        </span>
    );
}

function TimingResults({ job }: { job: Job }) {
    if (!job.total_seconds) return null;

    const items = [
        { label: "🔍 OCR + Xóa text", value: job.ocr_seconds, color: "#60a5fa" },
        { label: "🌐 Dịch thuật", value: job.translate_seconds, color: "#fb923c" },
        { label: "⚡ Tổng cộng", value: job.total_seconds, color: "#34d399" },
    ];

    return (
        <div style={{
            padding: 16,
            background: "var(--bg-card)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            marginBottom: 16,
        }}>
            <h4 style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: 12, color: "var(--text-secondary)" }}>
                ⏱ Kết quả thời gian
            </h4>
            {items.map(({ label, value, color }) => (
                value != null && (
                    <div key={label} style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        padding: "6px 0",
                        borderBottom: "1px solid var(--border-subtle)",
                    }}>
                        <span style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{label}</span>
                        <span style={{
                            fontFamily: "'Courier New', monospace",
                            fontWeight: 700,
                            fontSize: "0.95rem",
                            color,
                        }}>
                            {value.toFixed(2)}s
                        </span>
                    </div>
                )
            ))}
        </div>
    );
}

export default function EditorPage({ params }: EditorPageProps) {
    const { jobId } = use(params);
    const [job, setJob] = useState<Job | null>(null);
    const [loading, setLoading] = useState(true);
    const [currentPage, setCurrentPage] = useState(0);
    const [selectedBubble, setSelectedBubble] = useState<Bubble | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const fetchJob = useCallback(async () => {
        try {
            const data = await getJob(parseInt(jobId));
            setJob(data);
            setLoading(false);

            // Stop polling when done
            if (["completed", "failed"].includes(data.status) && pollRef.current) {
                clearInterval(pollRef.current);
                pollRef.current = null;
            }
        } catch {
            setLoading(false);
        }
    }, [jobId]);

    useEffect(() => {
        fetchJob();
        pollRef.current = setInterval(fetchJob, 2000);
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [fetchJob]);

    if (loading) {
        return (
            <div className="page-wrapper" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "3rem", marginBottom: 16 }}>⏳</div>
                    <p style={{ color: "var(--text-secondary)" }}>Đang tải...</p>
                </div>
            </div>
        );
    }

    if (!job) {
        return (
            <div className="page-wrapper" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                <div style={{ textAlign: "center" }}>
                    <div style={{ fontSize: "3rem", marginBottom: 16 }}>❌</div>
                    <p style={{ color: "var(--text-secondary)" }}>Không tìm thấy job</p>
                    <a href="/" className="btn btn-secondary" style={{ marginTop: 16 }}>
                        ← Quay lại
                    </a>
                </div>
            </div>
        );
    }

    const isProcessing = !["completed", "failed"].includes(job.status);
    const page = job.pages[currentPage];

    return (
        <div className="page-wrapper">
            {/* ── Header ──────────────────────────── */}
            <header style={{
                padding: "12px 0",
                borderBottom: "1px solid var(--border-subtle)",
            }}>
                <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                        <a href="/" className="btn btn-secondary" style={{ padding: "4px 12px", fontSize: "0.85rem" }}>
                            ← Thoát
                        </a>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontSize: "1.2rem" }}>🎌</span>
                            <span style={{
                                fontWeight: 800,
                                background: "var(--gradient-primary)",
                                WebkitBackgroundClip: "text",
                                WebkitTextFillColor: "transparent",
                            }}>
                                MangaDich
                            </span>
                        </div>
                        <span style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginLeft: 4 }}>
                            / Job #{job.id}
                        </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                        {/* Live Timer */}
                        {isProcessing && (
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>⏱</span>
                                <LiveTimer startTime={job.processing_started_at} />
                            </div>
                        )}
                        {/* Final time */}
                        {job.total_seconds != null && !isProcessing && (
                            <div style={{
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                padding: "4px 12px",
                                background: "rgba(16,185,129,0.15)",
                                borderRadius: "100px",
                                border: "1px solid rgba(16,185,129,0.3)",
                            }}>
                                <span style={{ fontSize: "0.8rem" }}>⚡</span>
                                <span style={{
                                    fontFamily: "'Courier New', monospace",
                                    fontWeight: 700,
                                    color: "#34d399",
                                    fontSize: "0.9rem",
                                }}>
                                    {job.total_seconds.toFixed(2)}s
                                </span>
                            </div>
                        )}
                        <span className={`status-badge ${job.status}`}>
                            {job.status}
                        </span>
                        {job.pages.length > 1 && (
                            <div style={{ display: "flex", gap: 4 }}>
                                {job.pages.map((_, i) => (
                                    <button
                                        key={i}
                                        onClick={() => setCurrentPage(i)}
                                        className={`btn btn-icon ${i === currentPage ? "btn-primary" : "btn-secondary"}`}
                                        style={{ padding: "6px 12px", fontSize: "0.8rem" }}
                                    >
                                        {i + 1}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </header>

            {/* ── Processing Status ───────────────── */}
            {isProcessing && (
                <div className="container" style={{ padding: "8px 0" }}>
                    <JobStatusComponent status={job.status} errorMessage={job.error_message} />
                </div>
            )}

            {/* ── Editor ──────────────────────────── */}
            <div style={{ flex: 1, display: "flex", padding: "16px" }}>
                <div className="editor-layout" style={{ flex: 1 }}>
                    {/* Canvas Area */}
                    <div className="editor-canvas-wrapper">
                        {job.status === "completed" && page ? (
                            <CanvasEditor job={job} pageIndex={currentPage} />
                        ) : (
                            <div style={{
                                height: "100%",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                flexDirection: "column",
                                gap: 16,
                            }}>
                                {isProcessing ? (
                                    <>
                                        <div style={{
                                            width: 60, height: 60,
                                            borderRadius: "50%",
                                            border: "3px solid var(--border-subtle)",
                                            borderTopColor: "var(--accent-purple)",
                                            animation: "spin 1s linear infinite",
                                        }} />
                                        <p style={{ color: "var(--text-secondary)", fontSize: "1.1rem" }}>
                                            {job.status === "ocr" ? "🔍 Đang nhận diện chữ (OCR)..." :
                                                job.status === "inpainting" ? "🧹 Đang xóa text gốc..." :
                                                    job.status === "translating" ? "🌐 Đang dịch sang tiếng Việt..." :
                                                        "⏳ Đang khởi tạo..."}
                                        </p>
                                        {/* Big live timer in center */}
                                        <div style={{ marginTop: 8 }}>
                                            <LiveTimer startTime={job.processing_started_at} />
                                        </div>
                                        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
                                    </>
                                ) : job.status === "failed" ? (
                                    <div style={{ textAlign: "center" }}>
                                        <div style={{ fontSize: "3rem", marginBottom: 16 }}>⚠️</div>
                                        <h3 style={{ color: "var(--error-red)", marginBottom: 8 }}>Xử lý thất bại</h3>
                                        <p style={{ color: "var(--text-muted)", maxWidth: 400, margin: "0 auto" }}>
                                            {job.error_message || "Có lỗi xảy ra trong quá trình xử lý manga."}
                                        </p>
                                        <a href="/" className="btn btn-secondary" style={{ marginTop: 24 }}>
                                            ← Quay lại trang chủ
                                        </a>
                                    </div>
                                ) : (
                                    <p style={{ color: "var(--text-muted)" }}>Đang chờ xử lý...</p>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Sidebar — Bubble List + Timing */}
                    <div className="editor-sidebar">
                        {/* Timing Results */}
                        <TimingResults job={job} />

                        <h3 style={{ fontSize: "1rem", fontWeight: 700, marginBottom: 16 }}>
                            💬 Text Bubbles ({page?.bubbles?.length || 0})
                        </h3>

                        {/* Font size control for selected bubble */}
                        {selectedBubble && (
                            <div style={{
                                padding: 12,
                                background: "var(--bg-card)",
                                borderRadius: "var(--radius-md)",
                                border: "1px solid var(--accent-blue)",
                                marginBottom: 16,
                            }}>
                                <label style={{ display: "block", fontSize: "0.85rem", color: "var(--text-secondary)", marginBottom: 8 }}>
                                    Cỡ chữ: {selectedBubble.font_size}px
                                </label>
                                <input
                                    type="range"
                                    min="8" max="72"
                                    value={selectedBubble.font_size}
                                    onChange={(e) => {
                                        const newSize = parseInt(e.target.value);
                                        setSelectedBubble({ ...selectedBubble, font_size: newSize });
                                        // Update API in background
                                        updateBubble(selectedBubble.id, { font_size: newSize }).catch(() => {});
                                        
                                        // Emit custom event so CanvasEditor can sync the change
                                        const event = new CustomEvent("bubbleFontChanged", { 
                                            detail: { id: selectedBubble.id, fontSize: newSize } 
                                        });
                                        window.dispatchEvent(event);
                                    }}
                                    style={{ width: "100%" }}
                                />
                                <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 6, marginBottom: 0 }}>
                                    (Click đúp vào text trên ảnh để sửa nội dung)
                                </p>
                            </div>
                        )}

                        {page?.bubbles?.length ? (
                            page.bubbles.map((bubble) => (
                                <div
                                    key={bubble.id}
                                    className={`bubble-list-item ${selectedBubble?.id === bubble.id ? "selected" : ""}`}
                                    onClick={() => setSelectedBubble(bubble)}
                                >
                                    <div className="ocr-text">
                                        🔤 {bubble.ocr_text || "—"}
                                    </div>
                                    <div className="translated-text">
                                        🇻🇳 {bubble.edited_text || bubble.translated_text || "—"}
                                    </div>
                                </div>
                            ))
                        ) : (
                            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                                {isProcessing ? "Đang xử lý OCR..." : "Không có text bubble nào"}
                            </p>
                        )}

                        {/* Export button */}
                        {job.status === "completed" && (
                            <div style={{ marginTop: 20 }}>
                                <button
                                    className="btn btn-primary"
                                    style={{ width: "100%" }}
                                    onClick={() => {
                                        const canvas = document.querySelector("canvas");
                                        if (canvas) {
                                            const link = document.createElement("a");
                                            link.download = `mangadich_page_${currentPage + 1}.png`;
                                            link.href = canvas.toDataURL("image/png");
                                            link.click();
                                        }
                                    }}
                                >
                                    📥 Tải ảnh đã dịch
                                </button>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
