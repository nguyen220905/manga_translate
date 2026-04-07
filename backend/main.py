"""
MangaDich — FastAPI backend
"""
import os
os.environ["FLAGS_use_mkldnn"] = "0"      # tắt oneDNN (crash với PaddleOCR trên 1 số CPU)
os.environ["FLAGS_enable_pir_api"] = "0"  # tắt PIR executor

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import jobs, pages


def _run_migrations():
    """Thêm cột mới vào SQLite nếu chưa có (SQLite không hỗ trợ IF NOT EXISTS)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN mode VARCHAR(20) DEFAULT 'auto'"))
            conn.commit()
        except Exception:
            pass  # cột đã tồn tại


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    yield


app = FastAPI(
    title="MangaDich API",
    description="OCR → Inpaint → Dịch tiếng Việt",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles

app.include_router(jobs.router)
app.include_router(pages.router)


@app.get("/health")
async def health():
    return {"status": "ok"}

frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../frontend")
# Create the directory if it doesn't exist yet to prevent startup crashes
os.makedirs(frontend_path, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
