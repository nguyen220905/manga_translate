"""
Pipeline Service — Orchestrates the full translation pipeline:
Upload → OCR → Inpaint → Translate → Save

Optimized:
- OCR + Inpaint run in thread pools (non-blocking)
- Multiple pages processed concurrently
- Inpainting starts as soon as OCR finishes per page (no wait for all pages)
- Translation batches all bubbles per page in single API call
"""
import os
import asyncio
import time
import logging
from sqlalchemy.orm import Session
from models import Job, Page, Bubble, JobStatus
from services.ocr_service import run_ocr_async
from services.inpaint_service import inpaint_image_async
from services.translation_service import translate_bubbles

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
UPLOAD_DIR = os.path.abspath(UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _resolve_image_path(image_url: str) -> str:
    if os.path.isabs(image_url):
        return image_url
    return os.path.join(UPLOAD_DIR, image_url)


async def _process_page_ocr_and_inpaint(
    page_id: int,
    image_path: str,
    source_language: str,
    db_factory,
) -> list[dict]:
    """Process a single page: OCR → Inpaint (runs concurrently for multiple pages)."""
    t0 = time.time()

    # ── OCR ──
    ocr_results = await run_ocr_async(image_path, source_language)

    if not ocr_results:
        logger.info(f"Page {page_id}: no text found ({time.time()-t0:.1f}s)")
        return []

    # ── Save bubbles to DB ──
    db: Session = db_factory()
    try:
        for result in ocr_results:
            bubble = Bubble(
                page_id=page_id,
                x=result["x"],
                y=result["y"],
                width=result["width"],
                height=result["height"],
                ocr_text=result["text"],
                confidence=result.get("confidence", 1.0),
                font_size=max(12, min(28, int(result["height"] * 0.6))),
            )
            db.add(bubble)
        db.commit()
    finally:
        db.close()

    # ── Inpaint (immediately after OCR, don't wait for other pages) ──
    bboxes = [{"x": r["x"], "y": r["y"], "width": r["width"], "height": r["height"]} for r in ocr_results]
    inpainted_filename = f"inpainted_{os.path.basename(image_path)}"
    inpainted_path = os.path.join(UPLOAD_DIR, inpainted_filename)

    await inpaint_image_async(image_path, bboxes, inpainted_path)

    # Save inpainted URL
    db = db_factory()
    try:
        page = db.query(Page).filter(Page.id == page_id).first()
        if page:
            page.inpainted_image_url = inpainted_filename
            db.commit()
    finally:
        db.close()

    logger.info(f"Page {page_id}: OCR+inpaint done in {time.time()-t0:.1f}s")
    return ocr_results


async def process_job(job_id: int, db_factory):
    """
    Run the full pipeline for a job. Tracks timing for each step.
    """
    import datetime as dt

    total_t0 = time.time()
    db: Session = db_factory()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Extract data needed for concurrent processing while session is open
        pages_data = [
            {
                "id": p.id,
                "image_path": _resolve_image_path(p.original_image_url)
            } 
            for p in job.pages
        ]
        source_lang = job.source_language.value
        genre = job.genre.value

        # Mark processing start
        job.processing_started_at = dt.datetime.utcnow()
        job.status = JobStatus.OCR
        db.commit()
        # Keep session open or re-query for job updates later
        
        # ── Step 1+2: OCR + Inpaint (concurrent per page) ──────────
        ocr_t0 = time.time()

        tasks = []
        for p_data in pages_data:
            tasks.append(
                _process_page_ocr_and_inpaint(
                    p_data["id"], p_data["image_path"], source_lang, db_factory
                )
            )

        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        ocr_inpaint_time = time.time() - ocr_t0

        # Log any per-page errors
        for i, result in enumerate(page_results):
            if isinstance(result, Exception):
                logger.error(f"Page {pages_data[i]['id']} failed: {result}")

        # Update job timing
        job.ocr_seconds = round(ocr_inpaint_time, 2)
        job.inpaint_seconds = 0
        db.commit()

        # ── Step 3: Translation (concurrent per page) ──────────────
        translate_t0 = time.time()
        job.status = JobStatus.TRANSLATING
        db.commit()

        translate_tasks = []
        translate_page_ids = []

        for p_data in pages_data:
            # Get bubbles for this page
            page_id = p_data["id"]
            bubbles = db.query(Bubble).filter(Bubble.page_id == page_id).all()
            if not bubbles:
                continue
                
            bubble_data = [{"ocr_text": b.ocr_text, "text": b.ocr_text} for b in bubbles]
            translate_tasks.append(
                translate_bubbles(bubble_data, genre=genre, source_language=source_lang)
            )
            translate_page_ids.append(page_id)

        if translate_tasks:
            translation_results = await asyncio.gather(*translate_tasks, return_exceptions=True)

            for page_id, translations in zip(translate_page_ids, translation_results):
                if isinstance(translations, Exception):
                    logger.error(f"Translation failed for page {page_id}: {translations}")
                    continue
                
                # Update bubbles in DB
                bubbles = db.query(Bubble).filter(Bubble.page_id == page_id).all()
                for bubble, translation in zip(bubbles, translations):
                    bubble.translated_text = translation
            db.commit()

        translate_time = time.time() - translate_t0

        # ── Done — save all timing ───────────────────────────────
        total_time = time.time() - total_t0
        job.translate_seconds = round(translate_time, 2)
        job.total_seconds = round(total_time, 2)
        job.status = JobStatus.COMPLETED
        db.commit()

        logger.info(
            f"⏱ Job {job_id} done: OCR+Inpaint={ocr_inpaint_time:.1f}s, "
            f"Translate={translate_time:.1f}s, Total={total_time:.1f}s "
            f"({len(pages_data)} pages)"
        )

    except Exception as e:
        try:
            # Fresh session for error handling to be safe
            error_db = db_factory()
            job = error_db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error_message = str(e)[:500]
                job.total_seconds = round(time.time() - total_t0, 2)
                error_db.commit()
            error_db.close()
        except Exception as ex:
            logger.error(f"Error while saving job failure: {ex}")
        
        logger.error(f"Job {job_id} failed: {e}")
        raise
    finally:
        db.close()

