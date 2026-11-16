"""
Bilingual Deep Learning OCR & Recognition Engine.
Integrates GPU-accelerated PaddleOCR for high-accuracy Japanese and English architectural annotations.
Includes Levenshtein distance CER (Character Error Rate) and WER (Word Error Rate) computation.
"""

from __future__ import annotations
import os
import sys
import types
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["FLAGS_use_mkldnn"] = "0"
import math
from typing import List, Dict, Tuple, Any, Optional
from dataclasses import dataclass
import numpy as np
import cv2

# 1. Configure NVIDIA cuDNN and cuBLAS binary paths for CUDA GPU acceleration on Windows
_cudnn_bin = r"C:\Users\Karunakar\AppData\Roaming\Python\Python311\site-packages\nvidia\cudnn\bin"
_cublas_bin = r"C:\Users\Karunakar\AppData\Roaming\Python\Python311\site-packages\nvidia\cublas\bin"
if os.path.exists(_cudnn_bin):
    try:
        os.add_dll_directory(_cudnn_bin)
    except Exception:
        pass
    os.environ["PATH"] = _cudnn_bin + ";" + os.environ.get("PATH", "")
if os.path.exists(_cublas_bin):
    try:
        os.add_dll_directory(_cublas_bin)
    except Exception:
        pass
    os.environ["PATH"] = _cublas_bin + ";" + os.environ.get("PATH", "")

# 2. Safe shim for albumentations and langchain_text_splitters to avoid training-only conflicts
if "albumentations" not in sys.modules:
    sys.modules["albumentations"] = types.ModuleType("albumentations")
if "langchain_text_splitters" not in sys.modules:
    _m = types.ModuleType("langchain_text_splitters")
    class _DummySplitter:
        def __init__(self, *args, **kwargs): pass
    _m.RecursiveCharacterTextSplitter = _DummySplitter
    sys.modules["langchain_text_splitters"] = _m


@dataclass
class OCRTextItem:
    """Represents a detected and recognized text item."""
    text: str
    confidence: float
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    polygon: List[List[float]]  # 4 corner coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    orientation: int = 0  # 0, 90, 180, 270


class BilingualOCREngine:
    """Production bilingual OCR manager powered by PaddleOCR on CUDA GPU for Japanese architectural drawings."""

    def __init__(
        self,
        languages: List[str] = ["japan"],
        gpu: bool = True,
        min_confidence: float = 0.25,
        det_limit_side_len: int = 2400,
        det_db_box_thresh: float = 0.5,
        det_db_unclip_ratio: float = 1.6,
        det_db_max_candidates: int = 8000,
        **kwargs
    ):
        self.languages = languages
        self.gpu = gpu
        self.min_confidence = min_confidence
        self.det_limit_side_len = det_limit_side_len
        self.det_db_box_thresh = det_db_box_thresh
        self.det_db_unclip_ratio = det_db_unclip_ratio
        self.det_db_max_candidates = det_db_max_candidates
        self._paddle_ocr = None

    @property
    def use_paddle(self) -> bool:
        return True

    @property
    def gpu_available(self) -> bool:
        """Returns True if CUDA GPU acceleration is available for Paddle."""
        try:
            import paddle
            return paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
        except Exception:
            return False

    @property
    def paddle_ocr(self):
        """Lazy initializer for GPU-accelerated PaddleOCR Japanese recognition engine."""
        if self._paddle_ocr is None:
            try:
                import paddle
                from paddleocr import PaddleOCR
                use_cuda = self.gpu and paddle.is_compiled_with_cuda() and paddle.device.cuda.device_count() > 0
                self._paddle_ocr = PaddleOCR(
                    use_angle_cls=False,
                    lang="japan",
                    use_gpu=use_cuda,
                    show_log=False,
                    det_limit_side_len=self.det_limit_side_len,
                    det_limit_type="max",
                    det_db_thresh=0.3,
                    det_db_box_thresh=self.det_db_box_thresh,
                    det_db_unclip_ratio=self.det_db_unclip_ratio
                )
                # Blueprint sheets often contain >1000 annotations. PaddleOCR's DBNet defaults to
                # max_candidates=1000 in postprocess_op, which causes cv2.findContours to truncate
                # and drop half the page. Override max_candidates to preserve full-page detections.
                if hasattr(self._paddle_ocr, "text_detector") and hasattr(self._paddle_ocr.text_detector, "postprocess_op"):
                    self._paddle_ocr.text_detector.postprocess_op.max_candidates = self.det_db_max_candidates
            except Exception as e:
                print(f"PaddleOCR GPU initialization failed: {e}")
                self._paddle_ocr = None
        return self._paddle_ocr

    def release_gpu_memory(self) -> None:
        """Releases cached Paddle GPU memory so local LLM (Ollama) has full VRAM access."""
        try:
            import paddle
            if paddle.is_compiled_with_cuda():
                paddle.device.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception as e:
            print(f"Paddle GPU memory release notice: {e}")

    def recognize(
        self,
        image: np.ndarray,
        detect_orientation: bool = True
    ) -> List[OCRTextItem]:
        """
        Executes text detection and recognition on an image array using PaddleOCR on CUDA GPU.
        """
        if image is None or image.size == 0:
            return []

        if self.paddle_ocr is None:
            print("Warning: PaddleOCR is not initialized.")
            return []

        try:
            if hasattr(self.paddle_ocr, "text_detector") and hasattr(self.paddle_ocr.text_detector, "postprocess_op"):
                self.paddle_ocr.text_detector.postprocess_op.max_candidates = self.det_db_max_candidates

            if len(image.shape) == 2:
                paddle_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                paddle_img = image

            # Run PaddleOCR inference on GPU (Paddle handles high-res scaling and coordinate mapping natively)
            res = self.paddle_ocr.ocr(paddle_img, cls=False)
            items: List[OCRTextItem] = []
            if res and len(res) > 0 and res[0]:
                for line in res[0]:
                    box = line[0]
                    text, conf = line[1]

                    if float(conf) < self.min_confidence or not str(text).strip():
                        continue

                    poly_arr = np.array(box, dtype=np.float32)

                    x_min = float(np.min(poly_arr[:, 0]))
                    y_min = float(np.min(poly_arr[:, 1]))
                    x_max = float(np.max(poly_arr[:, 0]))
                    y_max = float(np.max(poly_arr[:, 1]))

                    w = x_max - x_min
                    h = y_max - y_min
                    orientation = 90 if h > w * 1.5 else 0

                    items.append(
                        OCRTextItem(
                            text=str(text).strip(),
                            confidence=float(conf),
                            bbox=[x_min, y_min, x_max, y_max],
                            polygon=[[float(pt[0]), float(pt[1])] for pt in box],
                            orientation=orientation
                        )
                    )

            return items
        except Exception as e:
            print(f"PaddleOCR GPU inference error: {e}")
            return []

    def recognize_crop(self, crop: np.ndarray) -> Tuple[str, float]:
        """Recognizes text within a pre-cropped bounding box using PaddleOCR."""
        if crop is None or crop.size == 0 or self.paddle_ocr is None:
            return "", 0.0

        try:
            res = self.paddle_ocr.ocr(crop, det=False, cls=False)
            if res and len(res) > 0 and res[0]:
                first = res[0]
                if isinstance(first, (list, tuple)) and len(first) > 0:
                    item = first[0] if isinstance(first[0], (list, tuple)) else first
                    text = str(item[0]).strip()
                    conf = float(item[1])
                    return text, conf
        except Exception as e:
            print(f"PaddleOCR recognize_crop error: {e}")

        return "", 0.0

    @staticmethod
    def compute_cer(reference: str, hypothesis: str) -> float:
        """
        Computes Character Error Rate (CER) via Levenshtein edit distance:
        CER = EditDistance(ref, hyp) / len(ref)
        """
        ref = reference.replace(" ", "")
        hyp = hypothesis.replace(" ", "")

        if len(ref) == 0:
            return 0.0 if len(hyp) == 0 else 1.0

        d = BilingualOCREngine._levenshtein_distance(ref, hyp)
        return min(1.0, d / len(ref))

    @staticmethod
    def compute_wer(reference: str, hypothesis: str) -> float:
        """Computes Word Error Rate (WER) using whitespace tokenization."""
        ref_words = reference.strip().split()
        hyp_words = hypothesis.strip().split()

        if len(ref_words) == 0:
            return 0.0 if len(hyp_words) == 0 else 1.0

        d = BilingualOCREngine._levenshtein_distance(ref_words, hyp_words)
        return min(1.0, d / len(ref_words))

    @staticmethod
    def _levenshtein_distance(s1: Any, s2: Any) -> int:
        """Standard dynamic programming Levenshtein distance."""
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]

        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,       # deletion
                    dp[i][j - 1] + 1,       # insertion
                    dp[i - 1][j - 1] + cost # substitution
                )

        return dp[m][n]


if __name__ == "__main__":
    ref = "吹付けロックウール t=25"
    hyp = "吹付けロックウール t=25"
    print("Exact Match CER:", BilingualOCREngine.compute_cer(ref, hyp))
