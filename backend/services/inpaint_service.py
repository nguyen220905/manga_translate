"""
Inpaint Service — xóa chữ gốc khỏi ảnh bằng OpenCV.

Chiến lược theo loại nền:
  - Nền trắng (bubble) → flood-fill trắng toàn bộ interior
  - Nền tối             → Navier-Stokes inpaint chỉ pixel tối
"""
import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="inpaint")


def _fill_white_interior(region: np.ndarray) -> np.ndarray:
    """
    Giữ nguyên đường viền bubble (stroke tối), fill trắng phần interior.
    Tránh artifact viền đen khi dùng cv2.inpaint trên nền trắng.
    """
    out = region.copy()
    gray = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)

    _, dark = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    outline = cv2.dilate(dark, k, iterations=1)

    out[cv2.bitwise_not(outline) > 0] = [255, 255, 255]
    return out


def _build_mask(img: np.ndarray, bboxes: list[dict]) -> np.ndarray:
    """Tạo mask inpainting cho từng bbox."""
    h, w = img.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)

    for bbox in bboxes:
        x, y = int(bbox["x"]), int(bbox["y"])
        bw, bh = int(bbox["width"]), int(bbox["height"])

        pad = 3
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(w, x + bw + pad), min(h, y + bh + pad)

        region = img[y1:y2, x1:x2]
        if region.size == 0:
            mask[y1:y2, x1:x2] = 255
            continue

        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        local_avg = cv2.GaussianBlur(gray.astype(np.float32), (15, 15), 0)
        brightness = float(np.mean(local_avg))
        std = float(gray.std())

        if brightness > 200 and std < 55:
            # Bubble trắng — fill trực tiếp, không inpaint
            img[y1:y2, x1:x2] = _fill_white_interior(region)
        else:
            # Nền tối — chỉ mask pixel tối trong vùng sáng
            in_bright = (local_avg > 155).astype(np.uint8) * 255
            dark = (gray < 100).astype(np.uint8) * 255
            text_px = cv2.bitwise_and(dark, in_bright)
            k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            mask[y1:y2, x1:x2] = cv2.bitwise_or(
                mask[y1:y2, x1:x2],
                cv2.dilate(text_px, k, iterations=1)
            )

    # Dilation nhẹ để lấp đường viền chữ
    k_final = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    return cv2.dilate(mask, k_final, iterations=1)


def _inpaint_sync(image_path: str, bboxes: list[dict], output_path: str) -> str:
    t0 = time.time()

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Không đọc được ảnh: {image_path}")

    mask = _build_mask(img, bboxes)

    if mask.any():
        try:
            img = cv2.inpaint(img, mask, inpaintRadius=5, flags=cv2.INPAINT_NS)
        except Exception:
            img = cv2.inpaint(img, mask, inpaintRadius=4, flags=cv2.INPAINT_TELEA)

    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    logger.info(f"Inpaint xong: {time.time()-t0:.2f}s ({len(bboxes)} vùng)")
    return output_path


async def inpaint_image_async(image_path: str, bboxes: list[dict], output_path: str) -> str:
    """Async wrapper — chạy inpainting trong thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_pool, _inpaint_sync, image_path, bboxes, output_path)
