"""
Jobs Router — Upload images, create jobs, trigger processing pipeline.
"""
import os
import asyncio
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from PIL import Image as PILImage

from database import get_db, SessionLocal
from models import Job, Page, Bubble, JobStatus, Genre, SourceLanguage
from schemas import JobCreate, JobResponse, JobListResponse
from services.pipeline import process_job, UPLOAD_DIR

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    source_language: str = Form("zh"),
    genre: str = Form("tu_tien"),
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Create a new translation job with uploaded images."""
    # Validate inputs
    if source_language not in [e.value for e in SourceLanguage]:
        raise HTTPException(400, f"Invalid source_language: {source_language}")
    if genre not in [e.value for e in Genre]:
        raise HTTPException(400, f"Invalid genre: {genre}")
    if not files:
        raise HTTPException(400, "No files uploaded")
    
    # Create job
    job = Job(
        source_language=SourceLanguage(source_language),
        genre=Genre(genre),
        status=JobStatus.UPLOADING,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Save uploaded files
    for i, file in enumerate(files):
        ext = os.path.splitext(file.filename or "image.png")[1].lower()
        if ext not in (".jpg", ".jpeg", ".png", ".webp"):
            ext = ".png"
        
        filename = f"job_{job.id}_page_{i+1}_{uuid.uuid4().hex[:8]}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        content = await file.read()
        with open(filepath, "wb") as f:
            f.write(content)
        
        # Get image dimensions
        try:
            with PILImage.open(filepath) as img:
                w, h = img.size
        except Exception:
            w, h = None, None
        
        page = Page(
            job_id=job.id,
            page_number=i + 1,
            original_image_url=filename,
            width=w,
            height=h,
        )
        db.add(page)
    
    db.commit()
    db.refresh(job)
    
    # Trigger background processing
    background_tasks.add_task(process_job, job.id, SessionLocal)
    
    return job


@router.get("", response_model=list[JobListResponse])
async def list_jobs(db: Session = Depends(get_db)):
    """List all jobs (most recent first)."""
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(50).all()
    result = []
    for job in jobs:
        result.append(JobListResponse(
            id=job.id,
            status=job.status.value,
            source_language=job.source_language.value,
            genre=job.genre.value,
            created_at=job.created_at,
            page_count=len(job.pages),
        ))
    return result


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job details with all pages and bubbles."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job
