import logging
import numpy as np
import easyocr
from .base import BaseOCR

logger = logging.getLogger(__name__)


class EasyOCREngine(BaseOCR):
    """EasyOCR — dùng cho tiếng Anh và fallback đa ngôn ngữ."""

    def __init__(self, langs: list[str] = ["en"], mag_ratio: float = 1.5):
        self.langs = langs
        self.mag_ratio = mag_ratio
        self.reader = None

    def load(self):
        self.reader = easyocr.Reader(self.langs, gpu=False, verbose=False)
        logger.info(f"[EasyOCR] Loaded langs={self.langs}")

    def extract(self, image: np.ndarray) -> list[dict]:
        raw = self.reader.readtext(
            image,
            batch_size=4,
            paragraph=False,
            text_threshold=0.3,
            low_text=0.2,
            canvas_size=2560,
            mag_ratio=self.mag_ratio,
        )

        results = []
        for i, (box, text, conf) in enumerate(raw):
            if conf < 0.2 or not text.strip():
                continue
            x = int(min(p[0] for p in box))
            y = int(min(p[1] for p in box))
            w = int(max(p[0] for p in box)) - x
            h = int(max(p[1] for p in box)) - y
            pad = 4
            results.append({
                "id": f"BUBBLE_{i}",
                "x": max(0, x - pad),
                "y": max(0, y - pad),
                "width": w + pad * 2,
                "height": h + pad * 2,
                "rotation": 0,
                "text": text.strip(),
            })

        logger.info(f"[EasyOCR] {len(results)} vùng text")
        return results
