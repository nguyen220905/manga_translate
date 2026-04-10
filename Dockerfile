# =============================================================================
# MangaDich — Dockerfile
# Multi-stage build: giảm image size & tận dụng Docker layer cache
# =============================================================================

# ── Stage 1: Builder — cài dependencies ──────────────────────────────────────
FROM python:3.11-slim AS builder

# System deps cần thiết để build các package C/C++ (numpy, opencv, paddle...)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements trước (tận dụng cache nếu file không đổi)
COPY backend/requirements.txt ./

# Cài vào --prefix để dễ copy sang stage 2
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime — image nhẹ, chỉ chứa runtime ─────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="MangaDich Team"
LABEL description="MangaDich — OCR → Inpaint → Dịch manga/manhwa sang tiếng Việt"

# System deps cho runtime:
#   libglib2.0-0  — GLib (OpenCV, PaddlePaddle)
#   libgl1        — OpenGL (OpenCV headless rendering)
#   libgomp1      — OpenMP (EasyOCR, numpy multithreading)
#   libgthread    — GThread (PaddleOCR)
#   libsm6, libxext6, libxrender1 — X11 libs (headless image processing)
#   curl          — healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages từ builder stage
COPY --from=builder /install /usr/local

# Tạo user non-root cho security
RUN groupadd -r mangadich && useradd -r -g mangadich -d /app -s /sbin/nologin mangadich

WORKDIR /app

# Copy source code
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Tạo thư mục uploads & đặt quyền
RUN mkdir -p /app/backend/uploads \
    && mkdir -p /app/data \
    && chown -R mangadich:mangadich /app

WORKDIR /app/backend

# Chuyển sang user non-root
USER mangadich

# Port mặc định
EXPOSE 8000

# Healthcheck — kiểm tra app sống
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Entrypoint
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
