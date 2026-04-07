import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from database import Base
import enum


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    OCR = "ocr"
    INPAINTING = "inpainting"
    TRANSLATING = "translating"
    COMPLETED = "completed"
    FAILED = "failed"


class Genre(str, enum.Enum):
    TU_TIEN = "tu_tien"
    DAM_MY = "dam_my"
    ROMANCE = "romance"
    HENTAI = "hentai"
    HIEN_DAI = "hien_dai"
    ACTION = "action"
    SHOUJO = "shoujo"


class SourceLanguage(str, enum.Enum):
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ENGLISH = "en"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    jobs = relationship("Job", back_populates="user")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(SAEnum(JobStatus), default=JobStatus.PENDING)
    source_language = Column(SAEnum(SourceLanguage), default=SourceLanguage.CHINESE)
    genre = Column(SAEnum(Genre), default=Genre.TU_TIEN)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    mode = Column(String(20), default="auto")
    # ── Timing fields (seconds) ──
    processing_started_at = Column(DateTime, nullable=True)
    ocr_seconds = Column(Float, nullable=True)
    inpaint_seconds = Column(Float, nullable=True)
    translate_seconds = Column(Float, nullable=True)
    total_seconds = Column(Float, nullable=True)

    user = relationship("User", back_populates="jobs")
    pages = relationship("Page", back_populates="job", cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    page_number = Column(Integer, default=1)
    original_image_url = Column(String(500), nullable=False)
    inpainted_image_url = Column(String(500), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    job = relationship("Job", back_populates="pages")
    bubbles = relationship("Bubble", back_populates="page", cascade="all, delete-orphan")


class Bubble(Base):
    __tablename__ = "bubbles"

    id = Column(Integer, primary_key=True, index=True)
    page_id = Column(Integer, ForeignKey("pages.id"), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    width = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    rotation = Column(Float, default=0.0)
    ocr_text = Column(Text, nullable=True)
    translated_text = Column(Text, nullable=True)
    edited_text = Column(Text, nullable=True)
    font_size = Column(Integer, default=16)
    confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    page = relationship("Page", back_populates="bubbles")
