"""
Inpainting Service — Fast text erasure using OpenCV.
Optimized: TELEA algorithm (faster), smaller radius, parallel-ready.
"""
import cv2
import numpy as np
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
import asyncio
import time
import logging

logger = logging.getLogger(__name__)

_inpaint_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="inpaint")


def _inpaint_sync(image_path: str, bboxes: list[dict], output_path: str) -> str:
    """Synchronous inpainting — runs in thread pool."""
    t0 = time.time()

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    h, w = img.shape[:2]

    # Create mask — white = areas to inpaint
    mask = np.zeros((h, w), dtype=np.uint8)

    for bbox in bboxes:
        x = int(bbox["x"])
        y = int(bbox["y"])
        bw = int(bbox["width"])
        bh = int(bbox["height"])

        expand = 2
        y1 = max(0, y - expand)
        x1 = max(0, x - expand)
        y2 = min(h, y + bh + expand)
        x2 = min(w, x + bw + expand)
        mask[y1:y2, x1:x2] = 255

    # TELEA is ~2x faster than NS with similar quality for text removal
    inpainted = cv2.inpaint(img, mask, inpaintRadius=4, flags=cv2.INPAINT_TELEA)

    cv2.imwrite(output_path, inpainted, [cv2.IMWRITE_JPEG_QUALITY, 92])
    logger.info(f"Inpaint done in {time.time()-t0:.2f}s ({len(bboxes)} regions)")
    return output_path


async def inpaint_image_async(
    image_path: str, bboxes: list[dict], output_path: str
) -> str:
    """Async wrapper — runs inpainting in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        _inpaint_pool, _inpaint_sync, image_path, bboxes, output_path
    )


# Keep sync version for backward compatibility
def inpaint_image(image_path: str, bboxes: list[dict], output_path: str) -> str:
    return _inpaint_sync(image_path, bboxes, output_path)
