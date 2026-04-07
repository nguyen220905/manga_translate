# MangaDich

Ứng dụng web dịch manga/comic sang tiếng Việt tự động, sử dụng AI để nhận diện chữ (OCR), xóa text gốc (inpainting) và dịch theo ngữ cảnh thể loại.

## Yêu cầu

- Python 3.10+
- Gemini API Key ([lấy tại đây](https://aistudio.google.com/app/apikey))

## Cài đặt & Chạy

**1. Clone và cài dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

**2. Tạo file `.env` từ mẫu:**
```bash
cp .env.example .env
# Điền GEMINI_API_KEY vào file .env
```

**3. Khởi động:**
```bash
uvicorn main:app --reload --port 8000
```

Truy cập [http://localhost:8000](http://localhost:8000) để sử dụng.

> Hoặc chạy file `start_app.bat` trên Windows.

## Tính năng

- Upload ảnh manga (JPG, PNG, WebP), hỗ trợ nhiều trang cùng lúc
- OCR chuyên biệt theo ngôn ngữ: MangaOCR (Nhật), PaddleOCR (Trung), EasyOCR (Hàn, Anh)
- Inpainting xóa text gốc khỏi ảnh bằng OpenCV
- Dịch sang tiếng Việt với Gemini 2.0 Flash, có ngữ cảnh thể loại (Tu Tiên, Hiện Đại, Hành Động, Shoujo)
- Editor inline: kéo thả, chỉnh cỡ chữ, sửa nội dung dịch trực tiếp trên ảnh
- Xuất ảnh đã dịch

## Cấu trúc dự án

```
project/
├── backend/
│   ├── main.py                  # FastAPI app, serve static frontend
│   ├── database.py              # SQLAlchemy + SQLite
│   ├── models.py                # ORM: Job, Page, Bubble
│   ├── schemas.py               # Pydantic schemas
│   ├── routers/
│   │   ├── jobs.py              # POST /api/jobs
│   │   └── pages.py             # GET/PUT /api/pages, /api/bubbles
│   ├── services/
│   │   ├── pipeline.py          # Điều phối OCR → Inpaint → Translate
│   │   ├── ocr_service.py       # Router ngôn ngữ → OCR engine
│   │   ├── inpaint_service.py   # Xóa text bằng OpenCV
│   │   ├── translation_service.py # Gọi Gemini API
│   │   └── ocr/
│   │       ├── manga_ocr.py     # Nhật
│   │       ├── chinese_ocr.py   # Trung
│   │       ├── korean_ocr.py    # Hàn
│   │       └── easy_ocr.py      # Đa ngôn ngữ (fallback)
│   ├── uploads/                 # Ảnh upload và ảnh đã inpaint
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Trang upload & cấu hình
│   ├── editor.html              # Workspace chỉnh sửa
│   ├── css/style.css
│   └── js/
│       ├── api.js               # Fetch wrapper gọi backend
│       ├── main.js              # Logic trang upload
│       └── editor.js            # Canvas editor
└── .env.example
```

## Ngôn ngữ nguồn hỗ trợ

| Ngôn ngữ | OCR Engine |
|---|---|
| Trung Quốc | EasyOCR `ch_sim` + CV2 bubble detection |
| Nhật Bản | MangaOCR |
| Hàn Quốc | EasyOCR `ko` + flood-fill detection |
| Tiếng Anh | EasyOCR `en` |
