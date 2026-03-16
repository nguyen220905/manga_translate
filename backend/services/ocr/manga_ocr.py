import numpy as np
from manga_ocr import MangaOcr
from paddleocr import PaddleOCR
from .base import BaseOCR
import logging

logger = logging.getLogger(__name__)

class MangaOCREngine(BaseOCR):
    def __init__(self):
        self.detector = None
        self.reader = None

    def load(self):
        # PaddleOCR detects layout/bubbles
        # Manga-OCR reads text highly accurately
        self.detector = PaddleOCR(use_textline_orientation=True, lang='japan')
        self.reader = MangaOcr()
        logger.info("[MangaOCR] Loaded for Japanese")

    def extract(self, image: np.ndarray) -> list[dict]:
        layout = self.detector.ocr(image, cls=True)
        results = []
        for i, line in enumerate(layout[0] or []):
            box, (_, conf) = line
            if conf < 0.5:
                continue
            
            x = int(min(p[0] for p in box))
            y = int(min(p[1] for p in box))
            w = int(max(p[0] for p in box)) - x
            h = int(max(p[1] for p in box)) - y

            # Crop region for Manga-OCR
            pad = 4
            crop_y1 = max(0, y - pad)
            crop_y2 = min(image.shape[0], y + h + pad)
            crop_x1 = max(0, x - pad)
            crop_x2 = min(image.shape[1], x + w + pad)
            
            crop = image[crop_y1:crop_y2, crop_x1:crop_x2]
            
            if crop.size == 0:
                continue
                
            text = self.reader(crop)

            results.append({
                "id": f"BUBBLE_{i}",
                "x": x, "y": y,
                "width": w, "height": h,
                "rotation": 0,
                "text": text
            })
        return results
