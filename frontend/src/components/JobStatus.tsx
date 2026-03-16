"use client";

interface JobStatusProps {
    status: string;
    errorMessage?: string | null;
}

const STEPS = [
    { key: "uploading", label: "Upload" },
    { key: "ocr", label: "OCR" },
    { key: "inpainting", label: "Xóa text" },
    { key: "translating", label: "Dịch" },
    { key: "completed", label: "Hoàn tất" },
];

const STEP_ORDER = ["pending", "uploading", "ocr", "inpainting", "translating", "completed"];

export default function JobStatus({ status, errorMessage }: JobStatusProps) {
    const currentIdx = STEP_ORDER.indexOf(status);

    if (status === "failed") {
        return (
            <div style={{ padding: "16px", textAlign: "center" }}>
                <span className="status-badge failed">Thất bại</span>
                {errorMessage && (
                    <p style={{ marginTop: 8, color: "var(--text-muted)", fontSize: "0.85rem" }}>
                        {errorMessage}
                    </p>
                )}
            </div>
        );
    }

    return (
        <div className="progress-steps">
            {STEPS.map((step, i) => {
                const stepIdx = STEP_ORDER.indexOf(step.key);
                const isDone = currentIdx > stepIdx;
                const isActive = status === step.key;

                return (
                    <div key={step.key} style={{ display: "contents" }}>
                        <div className={`progress-step ${isDone ? "done" : isActive ? "active" : ""}`}>
                            <div className="dot" />
                            <span>{step.label}</span>
                        </div>
                        {i < STEPS.length - 1 && (
                            <div className={`progress-connector ${isDone ? "done" : ""}`} />
                        )}
                    </div>
                );
            })}
        </div>
    );
}
