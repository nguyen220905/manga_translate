"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { getJob, getImageUrl, updateBubble, type Job, type Bubble } from "@/lib/api";

interface CanvasEditorProps {
    job: Job;
    pageIndex: number;
}

export default function CanvasEditor({ job, pageIndex }: CanvasEditorProps) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [editingBubble, setEditingBubble] = useState<Bubble | null>(null);
    const [editText, setEditText] = useState("");
    const [textareaPos, setTextareaPos] = useState({ x: 0, y: 0, w: 0, h: 0 });
    const [scale, setScale] = useState(1);
    const [imgLoaded, setImgLoaded] = useState(false);
    const imageRef = useRef<HTMLImageElement | null>(null);
    const [selectedBubbleId, setSelectedBubbleId] = useState<number | null>(null);
    const [bubbles, setBubbles] = useState<Bubble[]>([]);
    const [dragState, setDragState] = useState<{
        bubbleId: number;
        startX: number;
        startY: number;
        origX: number;
        origY: number;
    } | null>(null);

    const page = job.pages[pageIndex];

    useEffect(() => {
        if (page) {
            setBubbles(page.bubbles || []);
        }
    }, [page]);

    // Listen for font size changes from the sidebar
    useEffect(() => {
        const handleFontChange = (e: Event) => {
            const customEvent = e as CustomEvent<{ id: number; fontSize: number }>;
            const { id, fontSize } = customEvent.detail;
            setBubbles((prev) =>
                prev.map((b) => (b.id === id ? { ...b, font_size: fontSize } : b))
            );
        };
        window.addEventListener("bubbleFontChanged", handleFontChange);
        return () => window.removeEventListener("bubbleFontChanged", handleFontChange);
    }, []);

    // Load the background image (inpainted or original)
    useEffect(() => {
        if (!page) return;
        const imgSrc = page.inpainted_image_url || page.original_image_url;
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            imageRef.current = img;
            setImgLoaded(true);
        };
        img.src = getImageUrl(imgSrc);
    }, [page]);

    // Calculate scale to fit container
    useEffect(() => {
        if (!containerRef.current || !page?.width || !page?.height) return;
        const containerW = containerRef.current.clientWidth;
        const containerH = containerRef.current.clientHeight;
        const scaleX = containerW / page.width;
        const scaleY = containerH / page.height;
        setScale(Math.min(scaleX, scaleY, 1));
    }, [page, imgLoaded]);

    // Render canvas
    const renderCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        const ctx = canvas?.getContext("2d");
        const img = imageRef.current;
        if (!canvas || !ctx || !img || !page) return;

        const w = page.width || img.naturalWidth;
        const h = page.height || img.naturalHeight;
        canvas.width = w * scale;
        canvas.height = h * scale;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.scale(scale, scale);

        // Draw background
        ctx.drawImage(img, 0, 0, w, h);

        // Draw bubbles
        for (const bubble of bubbles) {
            if (editingBubble && editingBubble.id === bubble.id) continue;

            const text = bubble.edited_text || bubble.translated_text || "";
            if (!text) continue;

            const isSelected = selectedBubbleId === bubble.id;

            // Draw bubble background (semi-transparent)
            ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
            ctx.strokeStyle = isSelected ? "#8b5cf6" : "rgba(0,0,0,0.1)";
            ctx.lineWidth = isSelected ? 3 : 1;

            const bx = bubble.x;
            const by = bubble.y;
            const bw = bubble.width;
            const bh = bubble.height;

            ctx.save();
            if (bubble.rotation) {
                ctx.translate(bx + bw / 2, by + bh / 2);
                ctx.rotate((bubble.rotation * Math.PI) / 180);
                ctx.translate(-(bx + bw / 2), -(by + bh / 2));
            }

            // Rounded rect
            const r = 4;
            ctx.beginPath();
            ctx.moveTo(bx + r, by);
            ctx.lineTo(bx + bw - r, by);
            ctx.quadraticCurveTo(bx + bw, by, bx + bw, by + r);
            ctx.lineTo(bx + bw, by + bh - r);
            ctx.quadraticCurveTo(bx + bw, by + bh, bx + bw - r, by + bh);
            ctx.lineTo(bx + r, by + bh);
            ctx.quadraticCurveTo(bx, by + bh, bx, by + bh - r);
            ctx.lineTo(bx, by + r);
            ctx.quadraticCurveTo(bx, by, bx + r, by);
            ctx.closePath();
            ctx.fill();
            ctx.stroke();

            // Auto-fit text
            const padding = 4;
            const maxW = bw - padding * 2;
            const maxH = bh - padding * 2;
            let fontSize = bubble.font_size || 16;

            // Shrink font if text overflows
            ctx.font = `500 ${fontSize}px Inter, sans-serif`;
            while (fontSize > 8) {
                ctx.font = `500 ${fontSize}px Inter, sans-serif`;
                const lines = wrapText(ctx, text, maxW);
                const totalH = lines.length * fontSize * 1.3;
                if (totalH <= maxH) break;
                fontSize -= 1;
            }

            // Draw text centered
            ctx.fillStyle = "#1a1a2e";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            const lines = wrapText(ctx, text, maxW);
            const lineH = fontSize * 1.3;
            const totalTextH = lines.length * lineH;
            const startY = by + (bh - totalTextH) / 2;

            for (let i = 0; i < lines.length; i++) {
                ctx.fillText(lines[i], bx + bw / 2, startY + i * lineH);
            }

            ctx.restore();
        }

        ctx.restore();
    }, [bubbles, scale, imgLoaded, editingBubble, selectedBubbleId, page]);

    useEffect(() => {
        if (imgLoaded) renderCanvas();
    }, [imgLoaded, renderCanvas]);

    // Word-wrap helper
    function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
        const words = text.split("");
        const lines: string[] = [];
        let currentLine = "";

        for (const char of words) {
            const testLine = currentLine + char;
            const { width } = ctx.measureText(testLine);
            if (width > maxWidth && currentLine) {
                lines.push(currentLine);
                currentLine = char;
            } else {
                currentLine = testLine;
            }
        }
        if (currentLine) lines.push(currentLine);
        return lines;
    }

    // Click handler — select or start editing
    const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / scale;
        const y = (e.clientY - rect.top) / scale;

        // Find clicked bubble
        const clicked = bubbles.find(
            (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height
        );

        if (clicked) {
            setSelectedBubbleId(clicked.id);
        } else {
            setSelectedBubbleId(null);
            if (editingBubble) finishEditing();
        }
    };

    // Double-click to edit
    const handleDoubleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / scale;
        const y = (e.clientY - rect.top) / scale;

        const clicked = bubbles.find(
            (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height
        );

        if (clicked) {
            startEditing(clicked);
        }
    };

    const startEditing = (bubble: Bubble) => {
        setEditingBubble(bubble);
        setEditText(bubble.edited_text || bubble.translated_text || "");
        setTextareaPos({
            x: bubble.x * scale,
            y: bubble.y * scale,
            w: bubble.width * scale,
            h: bubble.height * scale,
        });
    };

    const finishEditing = async () => {
        if (!editingBubble) return;
        try {
            await updateBubble(editingBubble.id, { edited_text: editText });
            setBubbles((prev) =>
                prev.map((b) =>
                    b.id === editingBubble.id ? { ...b, edited_text: editText } : b
                )
            );
        } catch (err) {
            console.error("Failed to save bubble:", err);
        }
        setEditingBubble(null);
    };

    // Mouse drag to move bubbles
    const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (editingBubble) return;
        const canvas = canvasRef.current;
        if (!canvas) return;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / scale;
        const y = (e.clientY - rect.top) / scale;

        const clicked = bubbles.find(
            (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height
        );

        if (clicked) {
            setDragState({
                bubbleId: clicked.id,
                startX: e.clientX,
                startY: e.clientY,
                origX: clicked.x,
                origY: clicked.y,
            });
        }
    };

    const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
        if (!dragState) return;
        const dx = (e.clientX - dragState.startX) / scale;
        const dy = (e.clientY - dragState.startY) / scale;
        setBubbles((prev) =>
            prev.map((b) =>
                b.id === dragState.bubbleId
                    ? { ...b, x: dragState.origX + dx, y: dragState.origY + dy }
                    : b
            )
        );
    };

    const handleMouseUp = async () => {
        if (!dragState) return;
        const moved = bubbles.find((b) => b.id === dragState.bubbleId);
        if (moved) {
            try {
                await updateBubble(moved.id, { x: moved.x, y: moved.y });
            } catch (err) {
                console.error("Failed to save position:", err);
            }
        }
        setDragState(null);
    };

    if (!page) {
        return <div style={{ padding: 40, color: "var(--text-muted)" }}>Không có trang nào</div>;
    }

    return (
        <div
            ref={containerRef}
            style={{ position: "relative", width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}
        >
            <canvas
                ref={canvasRef}
                onClick={handleCanvasClick}
                onDoubleClick={handleDoubleClick}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                style={{ cursor: dragState ? "grabbing" : "default", borderRadius: "8px" }}
            />

            {/* Inline editing textarea */}
            {editingBubble && (
                <textarea
                    className="inline-textarea"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    onBlur={finishEditing}
                    onKeyDown={(e) => {
                        if (e.key === "Escape") finishEditing();
                    }}
                    autoFocus
                    style={{
                        left: textareaPos.x,
                        top: textareaPos.y,
                        width: textareaPos.w,
                        height: textareaPos.h,
                        fontSize: `${(editingBubble.font_size || 14) * scale}px`,
                    }}
                />
            )}
        </div>
    );
}
