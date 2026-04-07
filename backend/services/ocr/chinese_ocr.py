"""
Chinese OCR Engine — tiếng Trung.

Phát hiện bubble qua CV2 (detect_text_regions),
sau đó chạy EasyOCR ch_sim trên từng crop riêng lẻ.
"""
import logging

import easyocr
import numpy as np

from .base import BaseOCR
from .manga_ocr import detect_text_regions

logger = logging.getLogger(__name__)

_JUNK = set("。、！？!?…　 \t\n.,")


def _is_junk(text: str) -> bool:
    t = text.strip()
    return not t or len(t) <= 1 or all(c in _JUNK for c in t)


class ChineseOCREngine(BaseOCR):
    """EasyOCR ch_sim trên từng bubble — tránh split bubble."""

    def __init__(self):
        self.reader = None

    def load(self):
        self.reader = easyocr.Reader(["ch_sim"], gpu=False, verbose=False)
        logger.info("[ChineseOCR] Loaded")

    def extract(self, image: np.ndarray) -> list[dict]:
        regions = detect_text_regions(image)
        logger.info(f"[ChineseOCR] {len(regions)} vùng candidate")

        results = []
        for i, (x, y, w, h) in enumerate(regions):
            crop = image[y:y + h, x:x + w]
            if crop.size == 0 or crop.std() < 12:
                continue

            try:
                lines = self.reader.readtext(crop, detail=0, paragraph=True)
                text = " ".join(lines).strip()
            except Exception as e:
                logger.debug(f"[ChineseOCR] EasyOCR lỗi vùng {i}: {e}")
                continue

            if _is_junk(text):
                continue

            results.append({
                "id": f"BUBBLE_{i}",
                "x": x, "y": y,
                "width": w, "height": h,
                "rotation": 0,
                "text": text,
            })

        logger.info(f"[ChineseOCR] {len(results)} bubble có text")
        return results
