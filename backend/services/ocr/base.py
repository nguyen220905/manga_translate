from abc import ABC, abstractmethod
import numpy as np

class BaseOCR(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model into memory — called once at startup"""
        pass

    @abstractmethod
    def extract(self, image: np.ndarray) -> list[dict]:
        """
        Takes numpy array image, returns list of text bubbles:
        [{ "id": "BUBBLE_0", "x": 10, "y": 20,
           "width": 100, "height": 50,
           "rotation": 0, "text": "..." }]
        """
        pass
