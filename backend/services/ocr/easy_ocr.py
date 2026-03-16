import easyocr
import numpy as np
from .base import BaseOCR

class EasyOCREngine(BaseOCR):
    def __init__(self, langs: list[str] = ['en']):
        self.langs = langs
        self.reader = None

    def load(self):
        # Using gpu=True for performance
        self.reader = easyocr.Reader(self.langs, gpu=True, verbose=False)
        print(f"[EasyOCR] Loaded for langs: {self.langs}")

    def extract(self, image: np.ndarray) -> list[dict]:
        if self.reader is None:
            raise RuntimeError("Model not loaded yet. Call load() first.")

        # Relax parameters to catch more text blocks across the comic page
        layout = self.reader.readtext(
            image, 
            batch_size=4, 
            paragraph=False, 
            text_threshold=0.3,   # Lowered from 0.6
            low_text=0.2,         # Lowered from 0.3
            canvas_size=2560,     # Allow reading larger pages
            mag_ratio=1.5         # Slight magnification for small text
        )
        
        results = []
        for i, (box, text, conf) in enumerate(layout):
            if conf < 0.2 or not text.strip():  # Lower confidence threshold

                continue
            x = int(min(p[0] for p in box))
            y = int(min(p[1] for p in box))
            w = int(max(p[0] for p in box)) - x
            h = int(max(p[1] for p in box)) - y
            
            # Simple padding
            pad = 4
            x = max(0, x - pad)
            y = max(0, y - pad)
            w = w + pad * 2
            h = h + pad * 2

            results.append({
                "id": f"BUBBLE_{i}",
                "x": x, "y": y,
                "width": w, "height": h,
                "rotation": 0,
                "text": text.strip()
            })
        return results
