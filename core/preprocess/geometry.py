"""
Document Geometry, Deskewing & Adaptive Contrast Normalization Engine.
Detects scanner tilt using Hough Line Transforms on structural CAD features,
deskews the drawing with bicubic affine transformations, and normalizes
uneven illumination and photocopy fade via morphological background subtraction.
"""

from __future__ import annotations
import math
from typing import Tuple, Dict, Any, Optional
import numpy as np
import cv2


class GeometryNormalizer:
    """Corrects document tilt, rotation, and lighting artifacts on blueprints."""

    def __init__(
        self,
        max_skew_angle: float = 10.0,
        min_line_length: int = 120,
        max_line_gap: int = 15
    ):
        self.max_skew_angle = max_skew_angle
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap

    def process(
        self,
        image: np.ndarray,
        apply_illumination_norm: bool = True,
        apply_line_separation: bool = False
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Full preprocessing pipeline:
        1. Detect skew angle
        2. Rotate image to 0.0 degrees
        3. Normalize uneven scanner lighting (non-destructive)
        4. Optional line separation (disabled by default to preserve text strokes)
        Returns: (processed_image, transformation_metadata)
        """
        # Ensure grayscale for analysis
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Detect Skew Angle
        skew_angle = self.detect_skew_angle(gray)

        # 2. Deskew if significant
        if abs(skew_angle) > 0.15:
            deskewed, rot_matrix = self.deskew(image, skew_angle)
        else:
            deskewed = image.copy()
            rot_matrix = np.eye(2, 3, dtype=np.float32)

        # 3. Illumination Normalization
        if apply_illumination_norm:
            normalized = self.normalize_illumination(deskewed)
        else:
            normalized = deskewed

        # 4. Adaptive Sauvola Binarization & Structural Line-Grid Separation
        if apply_line_separation:
            clean_text_img = self.separate_lines_and_text(normalized)
        else:
            clean_text_img = normalized

        metadata = {
            "detected_skew_angle": float(skew_angle),
            "deskew_applied": abs(skew_angle) > 0.15,
            "rotation_matrix": rot_matrix.tolist(),
            "original_shape": image.shape,
            "processed_shape": clean_text_img.shape,
            "display_image": deskewed
        }

        return clean_text_img, metadata

    def separate_lines_and_text(self, image: np.ndarray) -> np.ndarray:
        """
        Separates CAD structural lines and grid borders from text annotations
        using Sauvola adaptive binarization and directional morphological kernels.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # 1. Sauvola Local Adaptive Thresholding
        w = 25
        k = 0.2
        R = 128
        mean = cv2.blur(gray.astype(np.float32), (w, w))
        sq_mean = cv2.blur((gray.astype(np.float32)) ** 2, (w, w))
        variance = np.maximum(sq_mean - mean ** 2, 0)
        std = np.sqrt(variance)
        threshold = mean * (1.0 + k * (std / R - 1.0))
        bin_img = (gray >= threshold).astype(np.uint8) * 255
        inv = 255 - bin_img

        # 2. Extract structural horizontal and vertical CAD lines
        h_len = max(20, int(image.shape[1] // 35))
        v_len = max(20, int(image.shape[0] // 35))
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_len, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_len))

        h_lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(inv, cv2.MORPH_OPEN, v_kernel)
        lines = cv2.add(h_lines, v_lines)

        # Dilate line mask slightly to capture junctions touching text
        lines_dilated = cv2.dilate(lines, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)

        # 3. Subtract lines to obtain isolated text tokens
        text_only = cv2.subtract(inv, lines_dilated)
        clean_text = 255 - text_only

        if len(image.shape) == 3:
            return cv2.cvtColor(clean_text, cv2.COLOR_GRAY2BGR)
        return clean_text

    def detect_skew_angle(self, gray: np.ndarray) -> float:
        """
        Estimates scanner tilt by finding dominant horizontal lines in architectural walls/tables.
        Uses Canny edges + Probabilistic Hough Lines.
        """
        # Downsample for high-speed edge detection if image is massive
        h, w = gray.shape[:2]
        scale = 1.0
        if max(h, w) > 2000:
            scale = 2000.0 / max(h, w)
            proc_gray = cv2.resize(gray, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        else:
            proc_gray = gray

        # Otsu threshold + Canny edges
        edges = cv2.Canny(proc_gray, 50, 150, apertureSize=3)

        # Hough lines
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=80,
            minLineLength=int(self.min_line_length * scale),
            maxLineGap=int(self.max_line_gap * scale)
        )

        if lines is None or len(lines) == 0:
            return 0.0

        angles = []
        for line in lines:
            pts = line.ravel()
            if len(pts) < 4:
                continue
            x1, y1, x2, y2 = int(pts[0]), int(pts[1]), int(pts[2]), int(pts[3])
            dx = x2 - x1
            dy = y2 - y1

            if dx == 0:
                continue

            # In image screen coordinates where Y grows downwards:
            # A counter-clockwise tilt causes dy < 0.
            # Convert to standard Cartesian tilt: skew = -atan2(dy, dx)
            angle = -math.degrees(math.atan2(dy, dx))

            # Architectural CAD lines are primarily horizontal (near 0) or vertical (near 90 / -90)
            if abs(angle) <= self.max_skew_angle:
                angles.append(angle)
            elif abs(angle - 90) <= self.max_skew_angle:
                angles.append(angle - 90)
            elif abs(angle + 90) <= self.max_skew_angle:
                angles.append(angle + 90)

        if not angles:
            return 0.0

        median_angle = float(np.median(angles))
        return median_angle

    def deskew(self, image: np.ndarray, angle: float) -> Tuple[np.ndarray, np.ndarray]:
        """Rotates image by -angle around center with white background fill to level it."""
        h, w = image.shape[:2]
        center = (w / 2.0, h / 2.0)
        # Rotate by -angle to counteract the detected skew
        rot_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
        deskewed = cv2.warpAffine(
            image,
            rot_matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255) if len(image.shape) == 3 else 255
        )
        return deskewed, rot_matrix

    def normalize_illumination(self, image: np.ndarray) -> np.ndarray:
        """
        Removes uneven scanner lighting, photocopy shadows, and yellowing
        using morphological background approximation and division normalization.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            is_color = True
        else:
            gray = image
            is_color = False

        # Morphological closing (dilation followed by erosion) removes dark text/lines
        # to estimate the uneven background paper illumination
        k_size = 45
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (k_size, k_size))
        background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)

        # Avoid zero division
        background = np.maximum(background, 1)

        # Divide foreground by background: normalized = (gray / bg) * 255
        normalized = np.clip((gray.astype(np.float32) / background.astype(np.float32)) * 255.0, 0, 255).astype(np.uint8)

        if is_color:
            return cv2.cvtColor(normalized, cv2.COLOR_GRAY2BGR)
        return normalized


if __name__ == "__main__":
    normalizer = GeometryNormalizer()

    # Load degraded scanned blueprint from Stage 1
    sample_path = "data/output/degraded/ALFRED-DWG-1982-001_scanned.jpg"
    img = cv2.imread(sample_path)
    if img is not None:
        processed, meta = normalizer.process(img)
        print("Geometry normalizer completed successfully.")
        print(f"Detected Skew: {meta['detected_skew_angle']:.2f} degrees")
        print(f"Deskew Applied: {meta['deskew_applied']}")
        out_test_path = "data/output/degraded/ALFRED-DWG-1982-001_deskewed.jpg"
        cv2.imwrite(out_test_path, processed)
        print(f"Deskewed output saved to: {out_test_path}")
