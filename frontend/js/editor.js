document.addEventListener("DOMContentLoaded", () => {
    const urlParams = new URLSearchParams(window.location.search);
    const jobId = urlParams.get("id");
    
    if (!jobId) {
        window.location.href = "/";
        return;
    }

    // Elements
    const jobIdDisplay = document.getElementById("jobIdDisplay");
    const modeBadge = document.getElementById("modeBadge");
    const statusBadge = document.getElementById("statusBadge");
    const liveTimerContainer = document.getElementById("liveTimerContainer");
    const liveTimerTxt = document.getElementById("liveTimerTxt");
    const totalTimeContainer = document.getElementById("totalTimeContainer");
    const totalTimeTxt = document.getElementById("totalTimeTxt");
    const pagination = document.getElementById("pagination");
    
    const centerMessage = document.getElementById("centerMessage");
    const centerMessageTxt = document.getElementById("centerMessageTxt");
    const spinner = centerMessage.querySelector('.loading-spinner');
    
    const canvasContainer = document.getElementById("canvasContainer");
    const canvas = document.getElementById("editorCanvas");
    const ctx = canvas.getContext("2d");
    const inlineTextArea = document.getElementById("inlineTextArea");
    
    const exportContainer = document.getElementById("exportContainer");
    const exportBtn = document.getElementById("exportBtn");
    
    const timingResults = document.getElementById("timingResults");
    const timingItems = document.getElementById("timingItems");
    const bubbleCountTitle = document.getElementById("bubbleCountTitle");
    const bubbleListEl = document.getElementById("bubbleList");
    const fontControl = document.getElementById("fontControl");
    const fontSizeSlider = document.getElementById("fontSizeSlider");
    const fontSizeLabel = document.getElementById("fontSizeLabel");

    // State
    let currentJob = null;
    let currentPageIndex = 0;
    let bubbles = [];
    let scale = 1;
    let bgImage = null;
    let timerInterval = null;
    let pollingInterval = null;
    
    let selectedBubbleId = null;
    let editingBubbleInfo = null;
    let dragState = null; // { id, type:"move"|"resize", handle?, startX, startY, origX, origY, origW?, origH? }

    const HANDLE_R = 8; // screen pixels

    function getHandles(b) {
        return {
            nw: { cx: b.x,           cy: b.y,            cursor: "nwse-resize" },
            ne: { cx: b.x + b.width, cy: b.y,            cursor: "nesw-resize" },
            se: { cx: b.x + b.width, cy: b.y + b.height, cursor: "nwse-resize" },
            sw: { cx: b.x,           cy: b.y + b.height, cursor: "nesw-resize" },
        };
    }

    function hitHandle(imgX, imgY, bubble) {
        const r = HANDLE_R / scale;
        for (const [key, h] of Object.entries(getHandles(bubble))) {
            if (Math.hypot(imgX - h.cx, imgY - h.cy) <= r) return key;
        }
        return null;
    }

    jobIdDisplay.textContent = `/ Job #${jobId}`;

    function startTimer(startTimeString) {
        if (timerInterval) clearInterval(timerInterval);
        const utcStr = startTimeString.endsWith("Z") ? startTimeString : startTimeString + "Z";
        const start = new Date(utcStr).getTime();
        
        timerInterval = setInterval(() => {
            const elapsed = (Date.now() - start) / 1000;
            const mins = Math.floor(elapsed / 60);
            const secs = (elapsed % 60).toFixed(1);
            liveTimerTxt.textContent = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
        }, 100);
    }

    function stopTimer() {
        if (timerInterval) clearInterval(timerInterval);
        liveTimerContainer.style.display = "none";
    }

    async function loadJob() {
        try {
            currentJob = await getJob(jobId);
            renderUI();
            
            const isDoneOrReview = ["completed", "failed"].includes(currentJob.status);
            if (isDoneOrReview) {
                if (pollingInterval) {
                    clearInterval(pollingInterval);
                    pollingInterval = null;
                }
                stopTimer();
            } else if (!timerInterval && currentJob.processing_started_at) {
                liveTimerContainer.style.display = "flex";
                startTimer(currentJob.processing_started_at);
            }
        } catch (err) {
            console.error(err);
            centerMessageTxt.textContent = "Không tìm thấy job hoặc có lỗi xảy ra.";
            spinner.style.display = "none";
            if (pollingInterval) clearInterval(pollingInterval);
        }
    }

    pollingInterval = setInterval(loadJob, 2000);
    loadJob(); // Initial load

    function renderUI() {
        if (!currentJob) return;

        // Header Mode & Status
        modeBadge.style.background = "rgba(16,185,129,0.15)";
        modeBadge.style.color = "#34d399";
        modeBadge.style.border = "1px solid rgba(16,185,129,0.3)";
        modeBadge.textContent = "⚡ Tự động";

        statusBadge.textContent = currentJob.status;
        statusBadge.className = `status-badge ${currentJob.status}`;

        // Totals Check
        if (currentJob.total_seconds != null && ["completed", "failed"].includes(currentJob.status)) {
            totalTimeContainer.style.display = "flex";
            totalTimeTxt.textContent = `${currentJob.total_seconds.toFixed(2)}s`;
            renderTiming(currentJob);
        } else {
            totalTimeContainer.style.display = "none";
            timingResults.style.display = "none";
        }

        // Pagination
        pagination.innerHTML = "";
        if (currentJob.pages && currentJob.pages.length > 1) {
            currentJob.pages.forEach((p, idx) => {
                const btn = document.createElement("button");
                btn.className = `btn btn-icon ${idx === currentPageIndex ? "btn-primary" : "btn-secondary"}`;
                btn.style.padding = "6px 12px";
                btn.style.fontSize = "0.8rem";
                btn.textContent = idx + 1;
                btn.onclick = () => {
                    currentPageIndex = idx;
                    loadPageContent();
                };
                pagination.appendChild(btn);
            });
        }

        // Center Area
        const isProcessing = !["completed", "failed"].includes(currentJob.status);
        if (isProcessing) {
            canvasContainer.style.display = "none";
            centerMessage.style.display = "flex";
            spinner.style.display = "block";
            
            if (currentJob.status === "ocr") centerMessageTxt.textContent = "🔍 Đang nhận diện chữ (OCR)...";
            else if (currentJob.status === "inpainting") centerMessageTxt.textContent = "🧹 Đang xóa text gốc...";
            else if (currentJob.status === "translating") centerMessageTxt.textContent = "🌐 Đang dịch sang tiếng Việt...";
            else centerMessageTxt.textContent = "⏳ Đang khởi tạo...";
            
            exportContainer.style.display = "none";
        } else if (currentJob.status === "failed") {
            canvasContainer.style.display = "none";
            centerMessage.style.display = "flex";
            spinner.style.display = "none";
            centerMessageTxt.innerHTML = `<span style="font-size:3rem;display:block;margin-bottom:16px;">⚠️</span><strong style="color:var(--error-red)">Xử lý thất bại</strong><br>${currentJob.error_message || ""}`;
        } else {
            centerMessage.style.display = "none";
            canvasContainer.style.display = "flex";
            loadPageContent();
            exportContainer.style.display = "block";
        }
    }

    function renderTiming(job) {
        timingResults.style.display = "block";
        timingItems.innerHTML = "";
        const items = [
            { label: "🔍 OCR + Xóa text", value: job.ocr_seconds, color: "#60a5fa" },
            { label: "🌐 Dịch thuật", value: job.translate_seconds, color: "#fb923c" },
            { label: "⚡ Tổng cộng", value: job.total_seconds, color: "#34d399" },
        ];
        items.forEach(({label, value, color}) => {
            if (value != null) {
                const div = document.createElement("div");
                div.style = "display:flex; justify-content:space-between; padding: 6px 0; border-bottom: 1px solid var(--border-subtle);";
                div.innerHTML = `<span style="font-size:0.85rem;color:var(--text-secondary)">${label}</span>
                                 <span style="font-family:'Courier New', monospace; font-weight:700; font-size:0.95rem; color:${color}">${value.toFixed(2)}s</span>`;
                timingItems.appendChild(div);
            }
        });
    }

    function loadPageContent() {
        if (!currentJob || !currentJob.pages[currentPageIndex]) return;
        const page = currentJob.pages[currentPageIndex];
        
        // Deep copy bubbles to manage state locally
        if(!editingBubbleInfo) {
            bubbles = JSON.parse(JSON.stringify(page.bubbles || []));
            renderSidebar();
        }

        const imgSrc = page.inpainted_image_url || page.original_image_url;
        if (!bgImage || bgImage.dataset.src !== imgSrc) {
            const img = new Image();
            img.crossOrigin = "anonymous";
            img.dataset.src = imgSrc;
            img.onload = () => {
                bgImage = img;
                drawCanvas();
            };
            img.src = getImageUrl(imgSrc);
        } else {
            drawCanvas();
        }
    }

    function drawCanvas() {
        if (!bgImage || !currentJob) return;
        const page = currentJob.pages[currentPageIndex];
        
        const containerW = canvasContainer.clientWidth;
        const containerH = canvasContainer.clientHeight;
        const w = page.width || bgImage.naturalWidth;
        const h = page.height || bgImage.naturalHeight;
        
        const scaleX = containerW / w;
        const scaleY = containerH / h;
        scale = Math.min(scaleX, scaleY, 1);

        canvas.width = w * scale;
        canvas.height = h * scale;

        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.scale(scale, scale);

        ctx.drawImage(bgImage, 0, 0, w, h);

        bubbles.forEach(bubble => {
            if (editingBubbleInfo && editingBubbleInfo.id === bubble.id) return; // Skip drawing if currently editing

            const text = bubble.edited_text || bubble.translated_text || bubble.ocr_text || "";
            if (!text && currentJob.status === "completed") return;

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

            if (currentJob.status === "completed") {
                // Drawing text with word-wrap
                const isSelected = selectedBubbleId === bubble.id;
                
                const padding = 6;
                const isVerticalBox = bh > bw * 1.5;
                const maxW = bw - padding * 2;
                const maxH = bh - padding * 2;
                let fontSize = bubble.font_size || 14;

                ctx.font = `500 ${fontSize}px Inter, sans-serif`;
                while (fontSize > 8) {
                    ctx.font = `500 ${fontSize}px Inter, sans-serif`;
                    const lines = wrapText(ctx, text, maxW);
                    const totalH = lines.length * fontSize * 1.3;
                    if (totalH <= maxH) break;
                    fontSize -= 1;
                }

                const lines = wrapText(ctx, text, maxW);
                const lineH = fontSize * 1.3;
                const totalTextH = lines.length * lineH;
                const totalTextW = Math.max(...lines.map(l => ctx.measureText(l).width));

                const tPad = 5;
                const tx = bx + (bw - totalTextW) / 2 - tPad;
                const ty = isVerticalBox ? by + tPad : by + (bh - totalTextH) / 2 - tPad;
                const tw = totalTextW + tPad * 2;
                const th = totalTextH + tPad * 2;

                // Bubble background
                ctx.fillStyle = "rgba(255, 255, 255, 0.93)";
                ctx.strokeStyle = isSelected ? "#8b5cf6" : "rgba(0,0,0,0.15)";
                ctx.lineWidth = isSelected ? 2 : 1;

                const r = 4;
                ctx.beginPath();
                ctx.moveTo(tx + r, ty);
                ctx.lineTo(tx + tw - r, ty);
                ctx.quadraticCurveTo(tx + tw, ty, tx + tw, ty + r);
                ctx.lineTo(tx + tw, ty + th - r);
                ctx.quadraticCurveTo(tx + tw, ty + th, tx + tw - r, ty + th);
                ctx.lineTo(tx + r, ty + th);
                ctx.quadraticCurveTo(tx, ty + th, tx, ty + th - r);
                ctx.lineTo(tx, ty + r);
                ctx.quadraticCurveTo(tx, ty, tx + r, ty);
                ctx.closePath();
                ctx.fill();
                ctx.stroke();

                // Draw Text
                ctx.fillStyle = "#1a1a2e";
                ctx.textAlign = "center";
                ctx.textBaseline = "top";
                const startY = isVerticalBox ? by + tPad * 2 : by + (bh - totalTextH) / 2;

                for (let i = 0; i < lines.length; i++) {
                    ctx.fillText(lines[i], bx + bw / 2, startY + i * lineH);
                }
            }

            ctx.restore();
        });

        ctx.restore();
    }

    function wrapText(ctx, text, maxWidth) {
        if (!text) return [];
        const lines = [];
        const tokens = text.split(/(\s+)/);
        let currentLine = "";

        for (const token of tokens) {
            if (!token) continue;
            const testLine = currentLine + token;
            const { width } = ctx.measureText(testLine);

            if (width > maxWidth && currentLine.trim()) {
                lines.push(currentLine.trim());
                if (ctx.measureText(token.trim()).width > maxWidth) {
                    let partial = "";
                    for (const ch of token.trim()) {
                        if (ctx.measureText(partial + ch).width > maxWidth && partial) {
                            lines.push(partial);
                            partial = ch;
                        } else {
                            partial += ch;
                        }
                    }
                    currentLine = partial;
                } else {
                    currentLine = token;
                }
            } else {
                currentLine = testLine;
            }
        }
        if (currentLine.trim()) lines.push(currentLine.trim());
        return lines;
    }

    // Sidebar
    function renderSidebar() {
        bubbleCountTitle.textContent = `💬 Text Bubbles (${bubbles.length})`;
        bubbleListEl.innerHTML = "";

        // Font control is now rendered inline inside each selected bubble item
        fontControl.style.display = "none";

        bubbles.forEach(bubble => {
            const isSelected = selectedBubbleId === bubble.id;
            const div = document.createElement("div");
            div.className = `bubble-list-item ${isSelected ? 'selected' : ''}`;
            const ocr = bubble.ocr_text || "—";
            const trans = bubble.edited_text || bubble.translated_text || ocr || "—";
            const fontSize = bubble.font_size || 14;

            const fontControls = (currentJob && currentJob.status === "completed" && isSelected)
                ? `<div style="margin-top:10px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.1);">
                    <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:6px;">
                      <span style="font-size:0.78rem; color:var(--text-muted);">🔡 Cỡ chữ</span>
                      <span id="inlineFontLabel" style="font-size:0.82rem; font-weight:700; color:var(--accent-blue);">${fontSize}px</span>
                    </div>
                    <div style="display:flex; align-items:center; gap:6px;">
                      <button id="fontDecBtn" style="width:26px;height:26px;border-radius:50%;border:1px solid var(--border-subtle);background:var(--bg-elevated);color:var(--text-primary);cursor:pointer;font-size:1rem;line-height:1;display:flex;align-items:center;justify-content:center;">−</button>
                      <input type="range" id="inlineFontSlider" min="8" max="72" value="${fontSize}" style="flex:1;accent-color:var(--accent-blue);">
                      <button id="fontIncBtn" style="width:26px;height:26px;border-radius:50%;border:1px solid var(--border-subtle);background:var(--bg-elevated);color:var(--text-primary);cursor:pointer;font-size:1rem;line-height:1;display:flex;align-items:center;justify-content:center;">+</button>
                    </div>
                  </div>`
                : '';

            div.innerHTML = `
                <div class="ocr-text">🔤 ${ocr}</div>
                <div class="translated-text">🇻🇳 ${trans}</div>
                ${fontControls}
            `;

            div.onclick = (e) => {
                if (e.target.closest('#fontDecBtn, #fontIncBtn, #inlineFontSlider')) return;
                selectedBubbleId = bubble.id;
                renderSidebar();
                drawCanvas();
            };

            // Inline font controls
            if (isSelected && currentJob && currentJob.status === "completed") {
                const slider = div.querySelector('#inlineFontSlider');
                const label  = div.querySelector('#inlineFontLabel');
                const decBtn = div.querySelector('#fontDecBtn');
                const incBtn = div.querySelector('#fontIncBtn');

                const applySize = async (newSize) => {
                    newSize = Math.min(72, Math.max(8, newSize));
                    slider.value = newSize;
                    label.textContent = `${newSize}px`;
                    const bIdx = bubbles.findIndex(b => b.id === bubble.id);
                    if (bIdx >= 0) { bubbles[bIdx].font_size = newSize; drawCanvas(); }
                    try { await updateBubble(bubble.id, { font_size: newSize }); } catch(e) {}
                };

                slider.addEventListener('input', (e) => {
                    e.stopPropagation();
                    const newSize = parseInt(e.target.value);
                    label.textContent = `${newSize}px`;
                    const bIdx = bubbles.findIndex(b => b.id === bubble.id);
                    if (bIdx >= 0) { bubbles[bIdx].font_size = newSize; drawCanvas(); }
                });
                slider.addEventListener('change', (e) => {
                    e.stopPropagation();
                    applySize(parseInt(e.target.value));
                });
                decBtn.addEventListener('click', (e) => { e.stopPropagation(); applySize(parseInt(slider.value) - 1); });
                incBtn.addEventListener('click', (e) => { e.stopPropagation(); applySize(parseInt(slider.value) + 1); });
            }

            bubbleListEl.appendChild(div);
        });
    }

    fontSizeSlider.addEventListener("input", (e) => {
        const newSize = parseInt(e.target.value);
        fontSizeLabel.textContent = `Cỡ chữ: ${newSize}px`;
        
        const bIdx = bubbles.findIndex(b => b.id === selectedBubbleId);
        if (bIdx >= 0) {
            bubbles[bIdx].font_size = newSize;
            drawCanvas();
        }
    });

    fontSizeSlider.addEventListener("change", async (e) => {
        if (!selectedBubbleId) return;
        const newSize = parseInt(e.target.value);
        try {
            await updateBubble(selectedBubbleId, { font_size: newSize });
        } catch(e) {} // ignore bg error
    });

    // Canvas Interactions
    canvas.addEventListener("mousedown", (e) => {
        if (editingBubbleInfo) return;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / scale;
        const y = (e.clientY - rect.top) / scale;

        if (currentJob.status !== "completed") return;
        const clicked = bubbles.find(b => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height);
        if (clicked) {
            selectedBubbleId = clicked.id;
            dragState = {
                id: clicked.id, type: "move",
                startX: e.clientX, startY: e.clientY,
                origX: clicked.x, origY: clicked.y,
            };
            renderSidebar();
            drawCanvas();
        } else {
            selectedBubbleId = null;
            renderSidebar();
            drawCanvas();
        }
    });

    canvas.addEventListener("mousemove", (e) => {
        const rect = canvas.getBoundingClientRect();
        const mx = (e.clientX - rect.left) / scale;
        const my = (e.clientY - rect.top) / scale;

        if (!dragState) return;
        const dx = (e.clientX - dragState.startX) / scale;
        const dy = (e.clientY - dragState.startY) / scale;
        const bIdx = bubbles.findIndex(b => b.id === dragState.id);
        if (bIdx < 0) return;

        if (dragState.type === "resize") {
            const { handle, origX, origY, origW, origH } = dragState;
            let nx = origX, ny = origY, nw = origW, nh = origH;
            if      (handle === "nw") { nx = origX + dx; ny = origY + dy; nw = origW - dx; nh = origH - dy; }
            else if (handle === "ne") {                  ny = origY + dy; nw = origW + dx; nh = origH - dy; }
            else if (handle === "se") {                                   nw = origW + dx; nh = origH + dy; }
            else if (handle === "sw") { nx = origX + dx;                 nw = origW - dx; nh = origH + dy; }
            if (nw > 10) { bubbles[bIdx].x = nx; bubbles[bIdx].width = nw; }
            if (nh > 10) { bubbles[bIdx].y = ny; bubbles[bIdx].height = nh; }
            canvas.style.cursor = getHandles(bubbles[bIdx])[handle].cursor;
        } else {
            bubbles[bIdx].x = dragState.origX + dx;
            bubbles[bIdx].y = dragState.origY + dy;
            canvas.style.cursor = "grabbing";
        }
        drawCanvas();
    });

    const endDrag = async () => {
        if (!dragState) return;
        canvas.style.cursor = "default";
        const moved = bubbles.find(b => b.id === dragState.id);
        const savedState = dragState;
        dragState = null;

        if (moved) {
            try {
                if (savedState.type === "resize") {
                    await updateBubble(moved.id, { x: moved.x, y: moved.y, width: moved.width, height: moved.height });
                } else {
                    await updateBubble(moved.id, { x: moved.x, y: moved.y });
                }
            } catch(e) {}
        }
    };

    canvas.addEventListener("mouseup", endDrag);
    canvas.addEventListener("mouseleave", endDrag);

    // Double click to edit
    canvas.addEventListener("dblclick", (e) => {
        if (currentJob.status !== "completed") return;
        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / scale;
        const y = (e.clientY - rect.top) / scale;

        const clicked = bubbles.find(b => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height);
        if (clicked) {
            startEditing(clicked);
        }
    });

    function startEditing(bubble) {
        editingBubbleInfo = bubble;
        selectedBubbleId = bubble.id;
        
        inlineTextArea.style.display = "block";
        inlineTextArea.value = bubble.edited_text || bubble.translated_text || "";
        inlineTextArea.style.left = `${bubble.x * scale}px`;
        inlineTextArea.style.top = `${bubble.y * scale}px`;
        inlineTextArea.style.width = `${bubble.width * scale}px`;
        inlineTextArea.style.height = `${bubble.height * scale}px`;
        inlineTextArea.style.fontSize = `${(bubble.font_size || 14) * scale}px`;
        inlineTextArea.focus();
        
        drawCanvas();
    }

    async function stopEditing() {
        if (!editingBubbleInfo) return;
        const newText = inlineTextArea.value;
        inlineTextArea.style.display = "none";
        
        const bIdx = bubbles.findIndex(b => b.id === editingBubbleInfo.id);
        if (bIdx >= 0) {
            bubbles[bIdx].edited_text = newText;
            renderSidebar();
            drawCanvas();
            
            try {
                await updateBubble(editingBubbleInfo.id, { edited_text: newText });
            } catch(e){}
        }
        editingBubbleInfo = null;
        drawCanvas();
    }

    inlineTextArea.addEventListener("blur", stopEditing);
    inlineTextArea.addEventListener("keydown", (e) => {
        if (e.key === "Escape") stopEditing();
    });


    // Window Resize
    window.addEventListener("resize", () => {
        if (bgImage) drawCanvas();
    });

    // Export Button
    exportBtn.addEventListener("click", () => {
        const link = document.createElement("a");
        link.download = `mangadich_page_${currentPageIndex + 1}.png`;
        link.href = canvas.toDataURL("image/png");
        link.click();
    });
});
