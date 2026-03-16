"""
MangaDich Backend — FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
from routers import jobs, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    # Pre-warm OCR model in background thread (avoid cold-start on first request)
    import threading
    from services.ocr_service import preload_reader
    threading.Thread(target=preload_reader, args=("zh",), daemon=True).start()
    yield


app = FastAPI(
    title="MangaDich API",
    description="Manga/comic translation pipeline — OCR, inpainting, and Vietnamese translation",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(jobs.router)
app.include_router(pages.router)


@app.get("/")
async def root():
    return {"app": "MangaDich", "status": "running", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
