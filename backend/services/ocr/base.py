from abc import ABC, abstractmethod
import numpy as np


class BaseOCR(ABC):
    @abstractmethod
    def load(self) -> None:
        """Load model vào memory — gọi 1 lần lúc khởi động."""

    @abstractmethod
    def extract(self, image: np.ndarray) -> list[dict]:
        """
        Nhận ảnh numpy, trả về danh sách bubble:
        [{ "id": str, "x": int, "y": int,
           "width": int, "height": int,
           "rotation": float, "text": str }]
        """
