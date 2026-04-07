"""
MangaOCR Engine — dành cho manga Nhật.

Phát hiện bubble: CV2 connected components trên vùng trắng,
loại bỏ vùng chạm biên (= background) để chỉ giữ bubble thật.
"""
import logging
import re

import cv2
import numpy as np
from manga_ocr import MangaOcr
from PIL import Image as PILImage

from .base import BaseOCR

logger = logging.getLogger(__name__)

_HALLUCINATION = re.compile(r"^[\.…\-　\s。、！？!?~〜・ー]+$")


def _is_hallucination(text: str) -> bool:
    t = text.strip()
    return not t or len(t) <= 1 or bool(_HALLUCINATION.match(t))


def detect_text_regions(image: np.ndarray) -> list[tuple]:
    """
    Tìm speech bubble trên manga nền tối.
    Dùng connected components của vùng trắng, loại bỏ vùng chạm biên.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

    # Đóng các khe hở nhỏ trong viền bubble
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

    n_labels, labels = cv2.connectedComponents(closed)

    # Nhãn chạm biên = background, không phải bubble
    border_labels = set()
    for arr in [labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]:
        border_labels.update(arr.tolist())
    border_labels.discard(0)

    min_area = w * h * 0.001   # 0.1%
    max_area = w * h * 0.28    # 28%

    regions = []
    for lbl in range(1, n_labels):
        if lbl in border_labels:
            continue
        mask = (labels == lbl).astype(np.uint8)
        area = mask.sum()
        if area < min_area or area > max_area:
            continue

        ys, xs = np.where(mask)
        x, y = int(xs.min()), int(ys.min())
        bw = int(xs.max()) - x
        bh = int(ys.max()) - y

        if bw < 20 or bh < 20:
            continue
        aspect = bw / bh if bh > 0 else 0
        if aspect > 10 or aspect < 0.1:
            continue

        pad = 8
        regions.append((
            max(0, x - pad),
            max(0, y - pad),
            min(w - x, bw + pad * 2),
            min(h - y, bh + pad * 2),
        ))

    # Sắp xếp theo thứ tự đọc manga: trên xuống, phải sang trái
    regions.sort(key=lambda r: (r[1] // 60, -r[0]))
    return regions


class MangaOCREngine(BaseOCR):
    """MangaOCR — model chuyên biệt cho tiếng Nhật trong manga."""

    def __init__(self):
        self.reader = None

    def load(self):
        self.reader = MangaOcr()
        logger.info("[MangaOCR] Loaded")

    def extract(self, image: np.ndarray) -> list[dict]:
        regions = detect_text_regions(image)
        logger.info(f"[MangaOCR] {len(regions)} vùng candidate")

        results = []
        for i, (x, y, w, h) in enumerate(regions):
            crop = image[y:y + h, x:x + w]
            if crop.size == 0 or crop.std() < 12:
                continue

            text = self.reader(PILImage.fromarray(crop))
            if _is_hallucination(text):
                continue

            results.append({
                "id": f"BUBBLE_{i}",
                "x": x, "y": y,
                "width": w, "height": h,
                "rotation": 0,
                "text": text.strip(),
            })

        logger.info(f"[MangaOCR] {len(results)} bubble có text")
        return results
