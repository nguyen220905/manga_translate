import numpy as np
from paddleocr import PaddleOCR
from .base import BaseOCR
import logging

logger = logging.getLogger(__name__)

PADDLE_LANG_MAP = {
    'zh': 'ch',
    'ko': 'korean'
}

class PaddleOCREngine(BaseOCR):
    def __init__(self, lang: str = 'zh'):
        self.lang = PADDLE_LANG_MAP.get(lang, 'ch')
        self.reader = None

    def load(self):
        self.reader = PaddleOCR(use_textline_orientation=True, lang=self.lang)
        logger.info(f"[PaddleOCR] Loaded for lang: {self.lang}")

    def extract(self, image: np.ndarray) -> list[dict]:
        layout = self.reader.ocr(image, cls=True)
        results = []
        for i, line in enumerate(layout[0] or []):
            box, (text, conf) = line
            if conf < 0.5:
                continue
                
            x = int(min(p[0] for p in box))
            y = int(min(p[1] for p in box))
            w = int(max(p[0] for p in box)) - x
            h = int(max(p[1] for p in box)) - y
            
            results.append({
                "id": f"BUBBLE_{i}",
                "x": x, "y": y,
                "width": w, "height": h,
                "rotation": 0,
                "text": text
            })
        return results
