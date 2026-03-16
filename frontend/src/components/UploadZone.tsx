"use client";

import { useCallback, useState, useRef } from "react";

interface UploadZoneProps {
    files: File[];
    onFilesChange: (files: File[]) => void;
}

const ACCEPTED = ".jpg,.jpeg,.png,.webp";

export default function UploadZone({ files, onFilesChange }: UploadZoneProps) {
    const [dragOver, setDragOver] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleFiles = useCallback(
        (newFiles: FileList | null) => {
            if (!newFiles) return;
            const valid = Array.from(newFiles).filter((f) =>
                /\.(jpg|jpeg|png|webp)$/i.test(f.name)
            );
            onFilesChange([...files, ...valid]);
        },
        [files, onFilesChange]
    );

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            handleFiles(e.dataTransfer.files);
        },
        [handleFiles]
    );

    return (
        <div
            className={`upload-zone ${dragOver ? "drag-over" : ""}`}
            onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
        >
            <input
                ref={inputRef}
                type="file"
                multiple
                accept={ACCEPTED}
                style={{ display: "none" }}
                onChange={(e) => handleFiles(e.target.files)}
            />
            <div className="icon">📤</div>
            <h3>
                {files.length > 0
                    ? `${files.length} ảnh đã chọn`
                    : "Kéo thả ảnh manga vào đây"}
            </h3>
            <p>
                Hỗ trợ JPG, PNG, WebP · Có thể upload nhiều trang cùng lúc
            </p>
            {dragOver && (
                <div
                    style={{
                        position: "absolute",
                        inset: 0,
                        background: "rgba(139, 92, 246, 0.08)",
                        borderRadius: "inherit",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "1.2rem",
                        fontWeight: 600,
                        color: "var(--accent-purple)",
                    }}
                >
                    Thả ảnh vào đây!
                </div>
            )}
        </div>
    );
}
