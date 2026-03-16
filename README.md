# MangaDich — Manga Translation Web App

Translate manga/comic pages to Vietnamese with AI-powered OCR, inpainting, and a Canva-like inline editor.

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) and start translating!

## Features
- 📤 Upload manga pages (JPG/PNG/WebP)
- 🔍 OCR text extraction with bounding boxes
- 🧹 AI text erasure (inpainting)
- 🌐 Genre-aware Vietnamese translation (Tu Tiên, Đam Mỹ, Romance, 18+)
- ✏️ Canva-like inline editor (drag, resize, edit text)
- 💾 Export translated pages

## Project Structure (Cấu trúc dự án)

Dự án được ứng dụng kiến trúc Monorepo, chia làm 2 phần độc lập nhưng giao tiếp chặt chẽ qua REST API.

```text
MangaDich/
├── backend/                  # API và Backend xử lý AI (FastAPI, Python)
│   ├── main.py               # Entry point, khởi tạo app FastAPI và define các REST endpoints
│   ├── database.py           # Kết nối Database SQLite bằng SQLAlchemy
│   ├── models.py             # Các Table trong DB (Job, Page, Bubble)
│   ├── schemas.py            # Pydantic schemas để validate dữ liệu API (Input/Output)
│   ├── mangadich_v2.db       # File Database cục bộ hiện tại
│   └── services/             # Thư mục lõi chứa logic nghiệp vụ
│       ├── ocr_service.py    # Xử lý trích xuất chữ (EasyOCR, có thể mở rộng MangaOCR/PaddleOCR)
│       ├── inpaint_service.py# Thuật toán OpenCV để xóa mờ chữ dính trên viền ảnh
│       ├── translation_service.py # Gọi API OpenRouter (Gemini) theo ngữ cảnh (Tu tiên, Đam mỹ...)
│       └── pipeline.py       # Điều khiển luồng song song: OCR -> Inpaint -> Translation
├── frontend/                 # Giao diện người dùng (Next.js 16, React 19, TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css   # Biến CSS cho Dark theme, UI gradients
│   │   │   ├── layout.tsx    # Wrapper gốc của web
│   │   │   ├── page.tsx      # Landing page (Trang chủ) + Khu vực Upload file
│   │   │   └── editor/
│   │   │       └── [jobId]/page.tsx # Trang Workspace Edit (Hiển thị Editor, Đồng hồ Live timer)
│   │   ├── components/       # Các mảnh ghép UI tái sử dụng
│   │   │   ├── CanvasEditor.tsx # Bảng vẽ Canvas tương tác (Kéo thả chữ, trượt size)
│   │   │   ├── GenrePicker.tsx  # Component chọn thể loại truyện
│   │   │   ├── JobStatus.tsx    # Cảnh báo trạng thái xử lý
│   │   │   └── UploadZone.tsx   # Khu vực kéo thả file (Drag & Drop)
│   │   └── lib/
│   │       └── api.ts        # Các hàm Fetch gọi trực tiếp xuống Backend API
│   ├── package.json          # Node dependencies
│   └── next.config.ts        # Cấu hình Next.js
├── .env.example              # File biến môi trường mẫu (chứa API Keys)
└── README.md                 # Tài liệu mô tả dự án
```
