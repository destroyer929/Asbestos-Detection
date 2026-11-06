"""
Comprehensive OCR & Layout Evaluation & Ablation Benchmark Engine.
Measures:
1. Detection Precision, Recall, and F1 at IoU >= 0.3 / 0.5
2. Recognition Character Error Rate (CER) and Word Error Rate (WER)
3. Breakdown across Japanese vs English text
4. Ablation Study: Raw Degraded Scan vs Preprocessed & Deskewed Pipeline
"""

from __future__ import annotations
import math
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2

from models.ocr.engine import BilingualOCREngine
from core.preprocess.pipeline import PreprocessingPipeline


class OCREvaluator:
    """Evaluates text detection and recognition against pixel-accurate ground truth."""

    def __init__(self, iou_threshold: float = 0.3):
        self.iou_threshold = iou_threshold
        self.ocr_engine = BilingualOCREngine(gpu=True)
        self.preprocessor = PreprocessingPipeline(target_dpi=300)

    def evaluate_detection(
        self,
        ground_truth_boxes: List[List[float]],
        predicted_boxes: List[List[float]]
    ) -> Dict[str, float]:
        if not ground_truth_boxes and not predicted_boxes:
            return {"precision": 1.0, "recall": 1.0, "f1": 1.0, "tp": 0, "fp": 0, "fn": 0}
        if not ground_truth_boxes:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": len(predicted_boxes), "fn": 0}
        if not predicted_boxes:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "tp": 0, "fp": 0, "fn": len(ground_truth_boxes)}

        matched_gt = set()
        matched_pred = set()

        for p_idx, p_box in enumerate(predicted_boxes):
            best_iou = 0.0
            best_g_idx = -1
            for g_idx, g_box in enumerate(ground_truth_boxes):
                if g_idx in matched_gt:
                    continue
                iou = self._calculate_box_iou(p_box, g_box)
                if iou > best_iou:
                    best_iou = iou
                    best_g_idx = g_idx

            if best_iou >= self.iou_threshold and best_g_idx != -1:
                matched_gt.add(best_g_idx)
                matched_pred.add(p_idx)

        tp = len(matched_gt)
        fp = len(predicted_boxes) - len(matched_pred)
        fn = len(ground_truth_boxes) - len(matched_gt)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "precision": float(precision),
            "recall": float(recall),
            "f1": float(f1),
            "tp": tp,
            "fp": fp,
            "fn": fn
        }

    def evaluate_recognition(
        self,
        paired_text: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        if not paired_text:
            return {"mean_cer": 0.0, "mean_wer": 0.0, "japanese_cer": 0.0, "english_cer": 0.0}

        cers = []
        wers = []
        ja_cers = []
        en_cers = []

        for ref, hyp in paired_text:
            cer = BilingualOCREngine.compute_cer(ref, hyp)
            wer = BilingualOCREngine.compute_wer(ref, hyp)
            cers.append(cer)
            wers.append(wer)

            has_japanese = any('\u3040' <= char <= '\u30ff' or '\u4e00' <= char <= '\u9fff' for char in ref)
            if has_japanese:
                ja_cers.append(cer)
            else:
                en_cers.append(cer)

        return {
            "mean_cer": float(np.mean(cers)),
            "mean_wer": float(np.mean(wers)),
            "japanese_cer": float(np.mean(ja_cers)) if ja_cers else 0.0,
            "english_cer": float(np.mean(en_cers)) if en_cers else 0.0,
            "total_evaluated_strings": len(paired_text)
        }

    @staticmethod
    def _calculate_box_iou(boxA: List[float], boxB: List[float]) -> float:
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
        if interArea == 0.0:
            return 0.0

        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        return interArea / float(boxAArea + boxBArea - interArea)

