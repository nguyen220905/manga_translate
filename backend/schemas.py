from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ── Bubble ──────────────────────────────────────────────
class BubbleBase(BaseModel):
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    font_size: int = 16


class BubbleCreate(BubbleBase):
    ocr_text: str = ""
    translated_text: str = ""


class BubbleUpdate(BaseModel):
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    rotation: Optional[float] = None
    font_size: Optional[int] = None
    edited_text: Optional[str] = None
    translated_text: Optional[str] = None


class BubbleResponse(BubbleBase):
    id: int
    page_id: int
    ocr_text: Optional[str] = None
    translated_text: Optional[str] = None
    edited_text: Optional[str] = None
    confidence: float = 0.0

    class Config:
        from_attributes = True


# ── Page ────────────────────────────────────────────────
class PageResponse(BaseModel):
    id: int
    job_id: int
    page_number: int
    original_image_url: str
    inpainted_image_url: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    bubbles: list[BubbleResponse] = []

    class Config:
        from_attributes = True


# ── Job ─────────────────────────────────────────────────
class JobCreate(BaseModel):
    source_language: str = "zh"
    genre: str = "tu_tien"


class JobResponse(BaseModel):
    id: int
    status: str
    source_language: str
    genre: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processing_started_at: Optional[datetime] = None
    ocr_seconds: Optional[float] = None
    inpaint_seconds: Optional[float] = None
    translate_seconds: Optional[float] = None
    total_seconds: Optional[float] = None
    pages: list[PageResponse] = []

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    id: int
    status: str
    source_language: str
    genre: str
    created_at: datetime
    page_count: int = 0

    class Config:
        from_attributes = True
