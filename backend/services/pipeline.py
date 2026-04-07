"""
Pipeline Service — điều phối toàn bộ luồng xử lý.

OCR + Inpaint (song song theo trang) → Translate → Done
"""
import asyncio
import datetime as dt
import logging
import os
import time

from sqlalchemy.orm import Session

from models import Bubble, Job, JobStatus, Page
from services.inpaint_service import inpaint_image_async
from services.ocr_service import run_ocr_async
from services.translation_service import translate_bubbles

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _image_path(url: str) -> str:
    return url if os.path.isabs(url) else os.path.join(UPLOAD_DIR, url)


def _inpainted_path(original_path: str) -> tuple[str, str]:
    """Trả về (filename, full_path) của ảnh sau inpaint."""
    filename = f"inpainted_{os.path.basename(original_path)}"
    return filename, os.path.join(UPLOAD_DIR, filename)


def _make_bubbles(page_id: int, ocr_results: list[dict]) -> list[Bubble]:
    return [
        Bubble(
            page_id=page_id,
            x=r["x"], y=r["y"],
            width=r["width"], height=r["height"],
            ocr_text=r["text"],
            confidence=r.get("confidence", 1.0),
            font_size=max(10, min(18, int(r["height"] * 0.18))),
        )
        for r in ocr_results
    ]


async def _save_translations(page_id: int, translations: list[str], db: Session):
    """Lưu kết quả dịch vào DB."""
    bubbles = db.query(Bubble).filter(Bubble.page_id == page_id).all()
    for bubble, text in zip(bubbles, translations):
        bubble.translated_text = text
    db.commit()


def _fail_job(job_id: int, error: Exception, db_factory):
    """Đánh dấu job thất bại — dùng session mới để tránh conflict."""
    try:
        db = db_factory()
        job = db.query(Job).filter(Job.id == job_id).first()
        if job:
            job.status = JobStatus.FAILED
            job.error_message = str(error)[:500]
            db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Không lưu được lỗi cho job {job_id}: {e}")


# ── Auto mode ──────────────────────────────────────────────────────────────────

async def _process_page(page_id: int, image_path: str, lang: str, db_factory) -> list[dict]:
    """OCR → lưu bubble → Inpaint cho 1 trang (dùng trong auto mode)."""
    ocr_results = await run_ocr_async(image_path, lang)
    if not ocr_results:
        return []

    db: Session = db_factory()
    try:
        db.add_all(_make_bubbles(page_id, ocr_results))
        db.commit()
    finally:
        db.close()

    bboxes = [{"x": r["x"], "y": r["y"], "width": r["width"], "height": r["height"]} for r in ocr_results]
    filename, out_path = _inpainted_path(image_path)
    await inpaint_image_async(image_path, bboxes, out_path)

    db = db_factory()
    try:
        page = db.query(Page).filter(Page.id == page_id).first()
        if page:
            page.inpainted_image_url = filename
            db.commit()
    finally:
        db.close()

    return ocr_results


async def process_job(job_id: int, db_factory):
    """Auto mode: OCR + Inpaint (song song) → Translate → Done."""
    t0 = time.time()
    db: Session = db_factory()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        pages = [{"id": p.id, "path": _image_path(p.original_image_url)} for p in job.pages]
        lang, genre = job.source_language.value, job.genre.value

        job.processing_started_at = dt.datetime.utcnow()
        job.status = JobStatus.OCR
        db.commit()

        # Bước 1+2: OCR + Inpaint song song theo trang
        ocr_t0 = time.time()
        await asyncio.gather(
            *[_process_page(p["id"], p["path"], lang, db_factory) for p in pages],
            return_exceptions=True,
        )
        job.ocr_seconds = round(time.time() - ocr_t0, 2)

        # Bước 3: Dịch song song theo trang
        job.status = JobStatus.TRANSLATING
        db.commit()

        translate_t0 = time.time()
        tasks, page_ids = [], []
        for p in pages:
            bubbles = db.query(Bubble).filter(Bubble.page_id == p["id"]).all()
            if not bubbles:
                continue
            tasks.append(translate_bubbles(
                [{"ocr_text": b.ocr_text} for b in bubbles],
                genre=genre, source_language=lang,
            ))
            page_ids.append(p["id"])

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for page_id, translations in zip(page_ids, results):
                if isinstance(translations, Exception):
                    logger.error(f"Dịch thất bại trang {page_id}: {translations}")
                    continue
                await _save_translations(page_id, translations, db)

        total = time.time() - t0
        job.translate_seconds = round(time.time() - translate_t0, 2)
        job.total_seconds = round(total, 2)
        job.status = JobStatus.COMPLETED
        db.commit()
        logger.info(f"Job {job_id} hoàn tất: {total:.1f}s ({len(pages)} trang)")

    except Exception as e:
        _fail_job(job_id, e, db_factory)
        logger.error(f"Job {job_id} thất bại: {e}")
        raise
    finally:
        db.close()


