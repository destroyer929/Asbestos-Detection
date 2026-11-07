"""
Adaptive Document Quality & Noise Assessor (Pre-Flight Decision Brain).
Evaluates incoming architectural drawings to dynamically determine the optimal
preprocessing intensity, preventing destructive over-processing of clean blueprints
while applying deep restoration only when noisy or degraded.
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import cv2


class ProcessingIntensity(str, Enum):
    """Adaptive intensity profiles for blueprint preprocessing."""
    CLEAN_PASSTHROUGH = "CLEAN_PASSTHROUGH"           # Level 0: High-fidelity pass-through (zero destructive filtering)
    GENTLE_ENHANCEMENT = "GENTLE_ENHANCEMENT"         # Level 1: Geometric deskew + subtle contrast boost (no stroke erosion)
    AGGRESSIVE_RESTORATION = "AGGRESSIVE_RESTORATION" # Level 2: Heavy noise/smudge restoration (background division + Sauvola)


@dataclass
class QualityAssessment:
    """Pre-flight quality assessment decision and metric breakdown."""
    intensity: ProcessingIntensity
    intensity_level: int                                 # 0 = Pass-through, 1 = Gentle, 2 = Heavy
    sharpness: float                                     # Modified Laplacian variance
    noise_sigma: float                                   # Fast noise standard deviation (Immerkær method)
    contrast_range: float                                # Dynamic range ratio (P95 - P5) / 255.0
    skew_angle: float                                    # Detected geometric tilt in degrees
    bimodal_clarity: float                               # Otsu inter-class separability ratio [0.0 - 1.0]
    background_brightness: float                         # 95th percentile paper brightness [0 - 255]
    recommendation_reason: str                           # Human-readable engineering rationale
    applied_actions: List[str]                           # List of sanctioned preprocessing steps
    metrics_summary: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intensity": self.intensity.value,
            "intensity_level": self.intensity_level,
            "sharpness": round(self.sharpness, 1),
            "noise_sigma": round(self.noise_sigma, 2),
            "contrast_range": round(self.contrast_range, 3),
            "skew_angle": round(self.skew_angle, 2),
            "bimodal_clarity": round(self.bimodal_clarity, 3),
            "background_brightness": round(self.background_brightness, 1),
            "recommendation_reason": self.recommendation_reason,
            "applied_actions": self.applied_actions,
            "metrics_summary": self.metrics_summary,
        }


class DocumentQualityAssessor:
    """
    Intelligent pre-flight inspector.
    Computes physical image quality metrics in < 15ms and assigns an adaptive
    processing intensity profile to preserve fine Japanese Kanji and CAD strokes.
    """

    def __init__(
        self,
        clean_noise_threshold: float = 2.2,
        heavy_noise_threshold: float = 5.0,
        min_deskew_angle: float = 0.20,
        max_assessment_dim: int = 1500
    ):
        self.clean_noise_threshold = clean_noise_threshold
        self.heavy_noise_threshold = heavy_noise_threshold
        self.min_deskew_angle = min_deskew_angle
        self.max_assessment_dim = max_assessment_dim

    def assess(self, image: np.ndarray, detected_skew_angle: Optional[float] = None) -> QualityAssessment:
        """
        Analyzes image quality and returns a calibrated QualityAssessment.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        # 1. Downscale for fast multi-metric evaluation
        h, w = gray.shape[:2]
        if max(h, w) > self.max_assessment_dim:
            scale = float(self.max_assessment_dim) / float(max(h, w))
            eval_gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        else:
            eval_gray = gray

        # 2. Fast Noise Variance Estimation (Immerkær 1996)
        noise_sigma = self._estimate_noise_sigma(eval_gray)

        # 3. Edge Sharpness (Laplacian Energy)
        sharpness = float(cv2.Laplacian(eval_gray, cv2.CV_64F).var())

        # 4. Percentile Dynamic Range & Background Brightness
        p5, p95 = np.percentile(eval_gray, [5, 95])
        contrast_range = float((p95 - p5) / 255.0)
        bg_brightness = float(p95)

        # 5. Otsu Bimodal Separability Ratio
        bimodal_clarity = self._compute_bimodal_clarity(eval_gray)

        # 6. Skew Angle
        skew_angle = float(detected_skew_angle) if detected_skew_angle is not None else 0.0
        abs_skew = abs(skew_angle)

        # ----------------------------------------------------------------------
        # Pre-Flight Decision Engine
        # ----------------------------------------------------------------------
        actions: List[str] = []
        metrics_summary = {
            "noise_sigma": round(noise_sigma, 2),
            "sharpness": round(sharpness, 1),
            "contrast_range": round(contrast_range, 3),
            "skew_angle": round(skew_angle, 2),
            "bimodal_clarity": round(bimodal_clarity, 3),
            "background_brightness": round(bg_brightness, 1),
        }

        # Case 1: Pristine Clean Document (Level 0)
        # Low noise, bright paper background, negligible tilt
        is_clean_cad = (
            abs_skew < self.min_deskew_angle
            and noise_sigma <= self.clean_noise_threshold
            and bg_brightness >= 235.0
        )

        if is_clean_cad:
            intensity = ProcessingIntensity.CLEAN_PASSTHROUGH
            intensity_level = 0
            actions = ["RAW_IMAGE_PASSTHROUGH", "PRESERVE_FINE_STROKES"]
            reason = (
                f"Pristine document detected (Noise={noise_sigma:.2f}, BG Brightness={bg_brightness:.1f}, Skew={skew_angle:.2f}°). "
                f"Destructive filters bypassed to preserve 100% fine CJK stroke fidelity."
            )

        # Case 2: Heavy Noise / Yellowed / Degraded Blueprint (Level 2)
        # Genuinely degraded: heavy noise, severely darkened paper, or extreme tilt.
        # Strict protection: NEVER trigger aggressive restoration on clean white paper (BG >= 235, noise <= clean threshold).
        elif (
            (bg_brightness < 235.0 or noise_sigma > self.clean_noise_threshold)
            and (
                noise_sigma > self.heavy_noise_threshold
                or bg_brightness < 200.0
                or abs_skew > 3.0
                or (contrast_range < 0.40 and bg_brightness < 225.0)
            )
        ):
            intensity = ProcessingIntensity.AGGRESSIVE_RESTORATION
            intensity_level = 2
            if abs_skew >= self.min_deskew_angle:
                actions.append("HOUGH_AFFINE_DESKEW")
            actions.extend(["MORPHOLOGICAL_BG_NORMALIZATION", "ADAPTIVE_SAUVOLA_FILTERING"])
            reason = (
                f"Aged/degraded document detected (Noise={noise_sigma:.2f}, BG Brightness={bg_brightness:.0f}). "
                f"Applied full deep illumination leveling and adaptive noise suppression."
            )

        # Case 3: Moderate Scanned Document (Level 1 - Default Scanned Path)
        # Needs gentle straightening and mild contrast leveling without eating thin text
        else:
            intensity = ProcessingIntensity.GENTLE_ENHANCEMENT
            intensity_level = 1
            if abs_skew >= self.min_deskew_angle:
                actions.append("BICUBIC_DESKEW")
            actions.append("GENTLE_CONTRAST_ENHANCEMENT")
            actions.append("PRESERVE_STROKE_CONNECTIVITY")
            reason = (
                f"Standard scan detected (Noise={noise_sigma:.2f}, Skew={skew_angle:.2f}°). "
                f"Applied gentle geometric alignment and contrast enhancement without stroke erosion."
            )

        return QualityAssessment(
            intensity=intensity,
            intensity_level=intensity_level,
            sharpness=sharpness,
            noise_sigma=noise_sigma,
            contrast_range=contrast_range,
            skew_angle=skew_angle,
            bimodal_clarity=bimodal_clarity,
            background_brightness=bg_brightness,
            recommendation_reason=reason,
            applied_actions=actions,
            metrics_summary=metrics_summary,
        )

    def _estimate_noise_sigma(self, gray: np.ndarray) -> float:
        """
        Fast Noise Variance Estimation using 3x3 Laplacian mask (Immerkær 1996).
        Independent of structural edges.
        """
        H, W = gray.shape[:2]
        if H < 10 or W < 10:
            return 0.0

        M = np.array([
            [1, -2, 1],
            [-2, 4, -2],
            [1, -2, 1]
        ], dtype=np.float32)

        filtered = cv2.filter2D(gray.astype(np.float32), -1, M)
        sum_abs = np.sum(np.abs(filtered))
        sigma = (sum_abs * np.sqrt(0.5 * np.pi)) / (6.0 * (W - 2) * (H - 2))
        return float(sigma)

    def _compute_bimodal_clarity(self, gray: np.ndarray) -> float:
        """
        Computes Otsu's inter-class variance ratio (between-class variance / total variance).
        A high value (>= 0.85) indicates distinct, separated ink on paper.
        """
        total_var = float(np.var(gray))
        if total_var < 100.0 and np.mean(gray) > 230:
            # Clean white canvas with sparse CAD line art
            return 1.0

        if total_var < 1e-4:
            return 1.0  # Homogeneous or pure white

        thresh, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        w0 = float(np.mean(gray < thresh))
        w1 = float(np.mean(gray >= thresh))

        if w0 <= 1e-4 or w1 <= 1e-4:
            return 1.0 if np.mean(gray) > 220 else 0.5

        mean0 = float(np.mean(gray[gray < thresh]))
        mean1 = float(np.mean(gray[gray >= thresh]))

        between_var = w0 * w1 * ((mean0 - mean1) ** 2)
        return float(np.clip(between_var / total_var, 0.0, 1.0))
