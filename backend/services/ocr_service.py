"""
OCR Service — Router for manga text extraction engines.
Routes to Manga-OCR (JA), PaddleOCR (ZH, KO), EasyOCR (EN).
Optimized: engines loaded once at startup, image downscaling, thread pool execution.
"""
import numpy as np
from PIL import Image
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .ocr.easy_ocr import EasyOCREngine
from .ocr.manga_ocr import MangaOCREngine
from .ocr.paddle_ocr import PaddleOCREngine

logger = logging.getLogger(__name__)

# Max image dimension — downscale large images for speed
MAX_DIM = 1600

class OCRService:
    def __init__(self):
        # Load all engines once at startup
        logger.info("Initializing OCR engines...")
        self._engines = {
            'ja': MangaOCREngine(),
            'zh': PaddleOCREngine(lang='zh'),
            'ko': PaddleOCREngine(lang='ko'),
            'en': EasyOCREngine(langs=['en']),
        }
        for lang, engine in self._engines.items():
            try:
                engine.load()
            except Exception as e:
                logger.error(f"Failed to load OCR engine for {lang}: {e}")
        logger.info("All OCR engines ready.")

    def extract(self, image_path: str, lang: str) -> list[dict]:
        engine = self._engines.get(lang, self._engines['en'])
        
        # Open and downscale image for speed
        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size

        scale = 1.0
        if max(orig_w, orig_h) > MAX_DIM:
            scale = MAX_DIM / max(orig_w, orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
        
        image_np = np.array(img)
        
        # Run OCR
        results = engine.extract(image_np)
        
        # Scale back bboxes
        if scale != 1.0:
            inv_scale = 1.0 / scale
            for r in results:
                r["x"] = int(r["x"] * inv_scale)
                r["y"] = int(r["y"] * inv_scale)
                r["width"] = int(r["width"] * inv_scale)
                r["height"] = int(r["height"] * inv_scale)
                
        # Inject default confidence flag for pipeline backward compatibility
        for r in results:
            if "confidence" not in r:
                r["confidence"] = 1.0
                
        return results

# Singleton pattern - initialized at import time so models load at startup
ocr_service = OCRService()

# Thread pool for CPU-bound OCR
_ocr_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr")

async def run_ocr_async(image_path: str, source_language: str = "zh") -> list[dict]:
    """Async wrapper to run OCR in a thread pool without blocking the main event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        _ocr_pool,
        ocr_service.extract,
        image_path,
        source_language
    )

def preload_reader(source_language: str = "zh"):
    """Compatibility function. Engines are already loaded at startup."""
    pass
