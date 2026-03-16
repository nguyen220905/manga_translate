import numpy as np
from .base import BaseOCR
import logging

logger = logging.getLogger(__name__)

class GoogleVisionEngine(BaseOCR):
    def load(self):
        logger.info("[GoogleVision] Mock load (Cloud fallback not fully implemented)")
        pass

    def extract(self, image: np.ndarray) -> list[dict]:
        # Fallback stub
        return []
