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

# 2. Initialize PyTorch DLL paths and import EasyOCR
try:
    import torch
    import easyocr
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
    """Production bilingual OCR manager with CUDA GPU acceleration for Japanese architectural blueprints."""

    def __init__(
        self,
        languages: List[str] = ["ja", "en"],
        gpu: bool = True,
        min_confidence: float = 0.25,
        use_paddle: bool = False,
        **kwargs
    ):
        cuda_ok = False
        try:
            import torch
            cuda_ok = torch.cuda.is_available()
        except Exception:
            pass

        self.languages = languages
        self.gpu = gpu and cuda_ok
        self.min_confidence = min_confidence
        self.use_paddle = use_paddle
        self._reader: Optional[Any] = None
        self._paddle_ocr = None

    @property
    def gpu_available(self) -> bool:
        """Returns True if CUDA GPU acceleration is available."""
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    @property
    def reader(self):
        """Lazy initializer for GPU-accelerated PyTorch EasyOCR Reader."""
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(self.languages, gpu=self.gpu, verbose=False)
        return self._reader

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

    def release_gpu_memory(self) -> None:
        """Releases cached PyTorch GPU memory so the local LLM has full VRAM headroom."""
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            import gc
            gc.collect()
        except Exception as e:
            print(f"GPU memory release notice: {e}")

    def recognize(
        self,
        image: np.ndarray,
        detect_orientation: bool = True
    ) -> List[OCRTextItem]:
        """
        Executes hardware-accelerated text detection and recognition on an image array.
        Uses CUDA-accelerated PyTorch EasyOCR on GPU (primary) for fast inference (~5-10s).
        """
        if image is None or image.size == 0:
            return []

        # If user explicitly requested paddle and paddle_ocr is initialized
        if self.use_paddle and self.paddle_ocr is not None:
            try:
                orig_h, orig_w = image.shape[:2]
                max_dim = max(orig_h, orig_w)
                scale = 2400.0 / float(max_dim) if max_dim > 2400 else 1.0
                paddle_img = cv2.resize(image, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1.0 else image

                preds = self.paddle_ocr.predict(paddle_img)
                if preds and len(preds) > 0:
                    res = preds[0]
                    texts = res.get("rec_texts", [])
                    scores = res.get("rec_scores", [])
                    boxes = res.get("rec_boxes", [])
                    polys = res.get("dt_polys", [])

                    items: List[OCRTextItem] = []
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
                    if len(items) >= 5:
                        return items
            except Exception as e:
                print(f"PaddleOCR inference exception: {e}")

        # Primary High-Speed GPU Path: PyTorch CRAFT Detector + Recognition
        orig_h, orig_w = image.shape[:2]
        proc_img = image
        scale_x = 1.0
        scale_y = 1.0

        # Optimal blueprint resolution scaling for GPU memory & speed
        if orig_w > 3000 or orig_h > 3000:
            target_w = 2400
            scale = target_w / float(orig_w)
            target_h = int(orig_h * scale)
            proc_img = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)
            scale_x = orig_w / float(target_w)
            scale_y = orig_h / float(target_h)

        try:
            raw_results = self.reader.readtext(
                proc_img,
                detail=1,
                paragraph=False,
                min_size=6,
                text_threshold=0.35,
                low_text=0.20,
                link_threshold=0.25,
                canvas_size=2800,
                mag_ratio=1.3,
                add_margin=0.15
            )

            items: List[OCRTextItem] = []
            for poly, text, conf in raw_results:
                if conf < self.min_confidence or not text.strip():
                    continue

                poly_arr = np.array(poly, dtype=np.float32)
                poly_arr[:, 0] *= scale_x
                poly_arr[:, 1] *= scale_y

                x_min = float(np.min(poly_arr[:, 0]))
                y_min = float(np.min(poly_arr[:, 1]))
                x_max = float(np.max(poly_arr[:, 0]))
                y_max = float(np.max(poly_arr[:, 1]))

                w = x_max - x_min
                h = y_max - y_min
                orientation = 90 if h > w * 1.5 else 0

                items.append(
                    OCRTextItem(
                        text=text.strip(),
                        confidence=float(conf),
                        bbox=[x_min, y_min, x_max, y_max],
                        polygon=poly_arr.tolist(),
                        orientation=orientation
                    )
                )

            return items
        except Exception as e:
            print(f"GPU OCR recognition error: {e}")
            return []

    def recognize_crop(self, crop: np.ndarray) -> Tuple[str, float]:
        """Recognizes text within a pre-cropped bounding box."""
        if crop is None or crop.size == 0:
            return "", 0.0

        try:
            res = self.reader.readtext(crop, detail=1)
            if res:
                texts = [r[1] for r in res]
                confs = [r[2] for r in res]
                return " ".join(texts), float(np.mean(confs))
        except Exception as e:
            print(f"recognize_crop error: {e}")

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
