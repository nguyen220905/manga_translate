"""
OCR Service — routes mỗi ngôn ngữ sang engine phù hợp, chạy trong thread pool.

Engines:
  ja → MangaOCREngine   (model chuyên manga Nhật)
  zh → ChineseOCREngine (CV2 bubble detect + EasyOCR ch_sim)
  ko → KoreanOCREngine  (flood-fill detect + EasyOCR ko)
  en → EasyOCREngine    (EasyOCR en)
"""
import asyncio
import logging
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

from .ocr.manga_ocr import MangaOCREngine
from .ocr.chinese_ocr import ChineseOCREngine
from .ocr.korean_ocr import KoreanOCREngine
from .ocr.easy_ocr import EasyOCREngine

logger = logging.getLogger(__name__)

MAX_DIM = 1600  # giới hạn kích thước ảnh trước khi OCR (tăng tốc)


class OCRService:
    def __init__(self):
        self._engines = {
            "ja": MangaOCREngine(),
            "zh": ChineseOCREngine(),
            "ko": KoreanOCREngine(),
            "en": EasyOCREngine(langs=["en"]),
        }
        for lang, engine in self._engines.items():
            try:
                engine.load()
                logger.info(f"OCR engine [{lang}] loaded OK")
            except Exception as e:
                logger.error(f"OCR engine [{lang}] FAILED: {e}")

    def extract(self, image_path: str, lang: str) -> list[dict]:
        engine = self._engines.get(lang, self._engines["en"])

        img = Image.open(image_path).convert("RGB")
        orig_w, orig_h = img.size

        # Downscale nếu ảnh quá lớn
        scale = 1.0
        if max(orig_w, orig_h) > MAX_DIM:
            scale = MAX_DIM / max(orig_w, orig_h)
            img = img.resize((int(orig_w * scale), int(orig_h * scale)), Image.LANCZOS)

        results = engine.extract(np.array(img))

        # Scale bbox về kích thước gốc
        if scale != 1.0:
            inv = 1.0 / scale
            for r in results:
                r["x"] = int(r["x"] * inv)
                r["y"] = int(r["y"] * inv)
                r["width"] = int(r["width"] * inv)
                r["height"] = int(r["height"] * inv)

        for r in results:
            r.setdefault("confidence", 1.0)

        return results


# Singleton — load models 1 lần lúc khởi động
ocr_service = OCRService()

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ocr")


async def run_ocr_async(image_path: str, lang: str = "zh") -> list[dict]:
    """Chạy OCR trong thread pool để không block event loop."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_pool, ocr_service.extract, image_path, lang)
