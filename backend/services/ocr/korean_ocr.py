"""
Korean OCR Engine — tiếng Hàn (manhwa/webtoon + manga).

Phát hiện bubble tự động theo độ sáng trang:
  - Trang trắng (manhwa): flood-fill từ biên → vùng còn lại = bubble interior
  - Trang tối  (manga):   connected components vùng trắng (detect_text_regions)

OCR: EasyOCR ko với beamsearch trên từng crop — tránh split 1 bubble nhiều mảnh.
"""
import logging

import cv2
import easyocr
import numpy as np

from .base import BaseOCR
from .manga_ocr import detect_text_regions

logger = logging.getLogger(__name__)

_JUNK = set("。、！？!?…　 \t\n.,·-~ㅡ")


def _is_junk(text: str) -> bool:
    t = text.strip()
    return not t or len(t) <= 1 or all(c in _JUNK for c in t)


def _nms(boxes: list[tuple], iou_thr: float = 0.4) -> list[tuple]:
    """Non-maximum suppression — loại bỏ box trùng lặp, giữ box lớn nhất."""
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda b: b[2] * b[3], reverse=True)
    kept = []
    for box in boxes:
        x1, y1, w1, h1 = box
        skip = False
        for kx, ky, kw, kh in kept:
            ix = max(x1, kx); iy = max(y1, ky)
            iw = min(x1 + w1, kx + kw) - ix
            ih = min(y1 + h1, ky + kh) - iy
            if iw > 0 and ih > 0:
                inter = iw * ih
                union = w1 * h1 + kw * kh - inter
                if union > 0 and inter / union > iou_thr:
                    skip = True
                    break
        if not skip:
            kept.append(box)
    return kept


def _detect_webtoon_bubbles(image: np.ndarray) -> list[tuple]:
    """
    Tìm speech bubble trong manhwa/webtoon (nền trắng).

    Dùng flood-fill từ biên ảnh để xác định background,
    phần còn lại (flood == 255) = nằm bên trong đường viền bubble.
    """
    h, w = image.shape[:2]
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Seal khe hở nhỏ trong đường viền bubble
    _, dark = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    sealed = cv2.dilate(dark, k, iterations=1)
    white = cv2.bitwise_not(sealed)

    # Flood-fill background từ góc (0,0)
    flood = white.copy()
    cv2.floodFill(flood, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 128)

    # Vùng còn 255 = bị bao kín = interior của bubble
    enclosed = (flood == 255).astype(np.uint8) * 255
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(enclosed)

    min_area = w * h * 0.001   # 0.1%
    max_area = w * h * 0.12    # 12%

    regions = []
    for lbl in range(1, n_labels):
        area = int(stats[lbl, cv2.CC_STAT_AREA])
        if area < min_area or area > max_area:
            continue

        x  = int(stats[lbl, cv2.CC_STAT_LEFT])
        y  = int(stats[lbl, cv2.CC_STAT_TOP])
        bw = int(stats[lbl, cv2.CC_STAT_WIDTH])
        bh = int(stats[lbl, cv2.CC_STAT_HEIGHT])

        if bw < 25 or bh < 18:
            continue
        aspect = bw / bh if bh > 0 else 0
        if aspect > 7 or aspect < 0.12:
            continue

        # Phải đủ sáng (bubble trắng) và có text (không đồng màu)
        crop = image[y:y + bh, x:x + bw]
        if gray[y:y + bh, x:x + bw].mean() < 170 or crop.std() < 8:
            continue

        pad = 6
        regions.append((max(0, x - pad), max(0, y - pad),
                        min(w - x, bw + pad * 2), min(h - y, bh + pad * 2)))

    regions = _nms(regions)
    regions.sort(key=lambda r: (r[1] // 60, r[0]))
    logger.info(f"[KoreanOCR/webtoon] {len(regions)} bubble sau NMS")
    return regions


class KoreanOCREngine(BaseOCR):
    """EasyOCR ko với beamsearch, tự chọn chiến lược detect theo trang."""

    def __init__(self):
        self.reader = None

    def load(self):
        self.reader = easyocr.Reader(["ko"], gpu=False, verbose=False)
        logger.info("[KoreanOCR] Loaded")

    def extract(self, image: np.ndarray) -> list[dict]:
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        mean_brightness = float(gray.mean())

        if mean_brightness > 200:
            logger.info(f"[KoreanOCR] Trang trắng (mean={mean_brightness:.0f}) → webtoon detection")
            regions = _detect_webtoon_bubbles(image)
        else:
            logger.info(f"[KoreanOCR] Trang tối (mean={mean_brightness:.0f}) → manga detection")
            regions = detect_text_regions(image)

        logger.info(f"[KoreanOCR] {len(regions)} vùng candidate")

        results = []
        for i, (x, y, w, h) in enumerate(regions):
            crop = image[y:y + h, x:x + w]
            if crop.size == 0 or crop.std() < 8:
                continue

            try:
                lines = self.reader.readtext(
                    crop,
                    detail=0,
                    paragraph=True,
                    decoder="beamsearch",
                    beamWidth=10,
                    mag_ratio=2.0,
                    text_threshold=0.3,
                    low_text=0.2,
                )
                text = " ".join(lines).strip()
            except Exception as e:
                logger.debug(f"[KoreanOCR] EasyOCR lỗi vùng {i}: {e}")
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

        logger.info(f"[KoreanOCR] {len(results)} bubble có text")
        return results
