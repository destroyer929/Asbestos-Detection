"""
Bilingual Deep Learning OCR & Recognition Engine.
Integrates PaddleOCR v4 CJK for high-accuracy Japanese and English architectural annotations.
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

# 1. Safe shim for langchain_text_splitters to prevent paddlex from pulling in pyarrow on Windows (prevents 0xc0000005 access violation)
if "langchain_text_splitters" not in sys.modules:
    _m = types.ModuleType("langchain_text_splitters")
    class _DummySplitter:
        def __init__(self, *args, **kwargs): pass
    _m.RecursiveCharacterTextSplitter = _DummySplitter
    sys.modules["langchain_text_splitters"] = _m

# 2. Initialize PyTorch DLL paths for ModelScope/PaddleX dependencies on Windows
try:
    import torch
except ImportError:
    pass


@dataclass
class OCRTextItem:
    """Represents a detected and recognized text item."""
    text: str
    confidence: float
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    polygon: List[List[float]]  # 4 corner coordinates [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    orientation: int = 0  # 0, 90, 180, 270


class BilingualOCREngine:
    """Production bilingual OCR manager powered exclusively by PaddleOCR v4 CJK for Japanese architectural drawings."""

    def __init__(
        self,
        languages: List[str] = ["japan"],
        gpu: bool = True,
        min_confidence: float = 0.25,
        **kwargs
    ):
        self.languages = languages
        self.gpu = gpu
        self.min_confidence = min_confidence
        self._paddle_ocr = None

    @property
    def use_paddle(self) -> bool:
        return True

    @property
    def paddle_ocr(self):
        """Lazy initializer for PaddleOCR v4 CJK Japanese recognition engine."""
        if self._paddle_ocr is None:
            try:
                import paddle
                from paddleocr import PaddleOCR
                use_cuda = self.gpu and paddle.is_compiled_with_cuda()
                device = "gpu" if use_cuda else "cpu"
                self._paddle_ocr = PaddleOCR(
                    use_textline_orientation=False,
                    lang="japan",
                    enable_mkldnn=False,
                    device=device
                )
            except Exception as e:
                print(f"PaddleOCR initialization failed: {e}")
                self._paddle_ocr = None
        return self._paddle_ocr

    def recognize(
        self,
        image: np.ndarray,
        detect_orientation: bool = True
    ) -> List[OCRTextItem]:
        """
        Executes text detection and recognition on an image array.
        Uses PaddleOCR v4 CJK directly.
        """
        if image is None or image.size == 0:
            return []

        if self.paddle_ocr is None:
            print("Warning: PaddleOCR is not initialized.")
            return []

        try:
            orig_h, orig_w = image.shape[:2]
            max_dim = max(orig_h, orig_w)
            if max_dim > 2400:
                scale = 2400.0 / float(max_dim)
                paddle_img = cv2.resize(image, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            else:
                scale = 1.0
                paddle_img = image

            preds = self.paddle_ocr.predict(paddle_img)
            items: List[OCRTextItem] = []
            if preds and len(preds) > 0:
                res = preds[0]
                texts = res.get("rec_texts", [])
                scores = res.get("rec_scores", [])
                boxes = res.get("rec_boxes", [])
                polys = res.get("dt_polys", [])

                for box, poly, text, conf in zip(boxes, polys, texts, scores):
                    if float(conf) < self.min_confidence or not str(text).strip():
                        continue

                    x_min, y_min, x_max, y_max = [float(b) / scale for b in box]
                    scaled_poly = [[float(pt[0]) / scale, float(pt[1]) / scale] for pt in poly] if poly is not None else []
                    w = x_max - x_min
                    h = y_max - y_min
                    orientation = 90 if h > w * 1.5 else 0

                    items.append(
                        OCRTextItem(
                            text=str(text).strip(),
                            confidence=float(conf),
                            bbox=[x_min, y_min, x_max, y_max],
                            polygon=scaled_poly,
                            orientation=orientation
                        )
                    )
            return items
        except Exception as e:
            print(f"PaddleOCR inference exception: {e}")
            return []

    def recognize_crop(self, crop: np.ndarray) -> Tuple[str, float]:
        """Recognizes text within a pre-cropped bounding box."""
        if crop is None or crop.size == 0 or self.paddle_ocr is None:
            return "", 0.0

        try:
            preds = self.paddle_ocr.predict(crop)
            if preds and len(preds) > 0:
                res = preds[0]
                texts = res.get("rec_texts", [])
                scores = res.get("rec_scores", [])
                if texts:
                    avg_conf = float(np.mean(scores)) if scores else 0.8
                    return " ".join(str(t).strip() for t in texts), avg_conf
        except Exception as e:
            print(f"PaddleOCR recognize_crop exception: {e}")

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
