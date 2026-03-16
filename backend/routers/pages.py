"""
Pages & Bubbles Router — CRUD for pages and inline bubble editing.
"""
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models import Page, Bubble
from schemas import PageResponse, BubbleUpdate, BubbleResponse
from services.pipeline import UPLOAD_DIR

router = APIRouter(prefix="/api", tags=["pages"])


@router.get("/pages/{page_id}", response_model=PageResponse)
async def get_page(page_id: int, db: Session = Depends(get_db)):
    """Get a page with all its bubbles."""
    page = db.query(Page).filter(Page.id == page_id).first()
    if not page:
        raise HTTPException(404, "Page not found")
    return page


@router.put("/bubbles/{bubble_id}", response_model=BubbleResponse)
async def update_bubble(
    bubble_id: int,
    update: BubbleUpdate,
    db: Session = Depends(get_db),
):
    """Update a bubble's text or position (inline editing)."""
    bubble = db.query(Bubble).filter(Bubble.id == bubble_id).first()
    if not bubble:
        raise HTTPException(404, "Bubble not found")
    
    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(bubble, key, value)
    
    db.commit()
    db.refresh(bubble)
    return bubble


@router.get("/images/{filename}")
async def serve_image(filename: str):
    """Serve uploaded/inpainted images."""
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Image not found")
    return FileResponse(filepath)
