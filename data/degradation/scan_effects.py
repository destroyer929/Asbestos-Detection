"""
Realistic Scanner Degradation Pipeline for Architectural Drawings.
Simulates real-world aged blueprint defects: scanner skew, optical blur,
salt-and-pepper photocopy speckles, contrast fade, and intersecting line artifacts.
Critically, transforms ground-truth bounding polygons to maintain exact evaluation alignment.
"""

from __future__ import annotations
import math
import json
import random
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import cv2


class ScanDegradationEngine:
    """Applies realistic scanning and aging defects to synthetic clean drawings."""

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

    def degrade(
        self,
        image_path: Path | str,
        ground_truth_path: Path | str,
        output_image_path: Path | str,
        output_gt_path: Path | str,
        skew_angle: float = 1.8,
        blur_ksize: int = 3,
        noise_density: float = 0.008,
        photocopy_contrast: float = 0.85
    ) -> Dict[str, Any]:
        """
        Loads clean image & GT, applies physical scan defects, updates polygon
        coordinates via affine transformation, and saves degraded artifacts.
        """
        img = cv2.imread(str(image_path))
        if img is None:
            raise FileNotFoundError(f"Could not load image: {image_path}")

        with open(ground_truth_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)

        h, w = img.shape[:2]
        center = (w / 2.0, h / 2.0)

        # 1. Apply Affine Rotation & Skew
        rot_matrix = cv2.getRotationMatrix2D(center, skew_angle, 1.0)
        degraded = cv2.warpAffine(img, rot_matrix, (w, h), borderValue=(255, 255, 255), flags=cv2.INTER_LINEAR)

        # 2. Simulate Optical Scanner Blur
        if blur_ksize > 1:
            degraded = cv2.GaussianBlur(degraded, (blur_ksize, blur_ksize), 0)

        # 3. Simulate Photocopy Contrast Loss & Gray Shading
        degraded = cv2.convertScaleAbs(degraded, alpha=photocopy_contrast, beta=35)

        # 4. Simulate Salt and Pepper Speckle Dust
        degraded = self._add_speckle_noise(degraded, noise_density)

        # 5. Simulate Blueprint Roller Fold Creases / Faint Scanner Shadows
        degraded = self._add_scanner_crease(degraded)

        # 6. Update Ground-Truth Coordinates via Affine Matrix
        updated_annotations = []
        for anno in gt_data["annotations"]:
            poly = np.array(anno["polygon"], dtype=np.float32)
            # Transform polygon points: [x, y, 1] dot rot_matrix.T
            ones = np.ones((poly.shape[0], 1), dtype=np.float32)
            points_homogeneous = np.hstack([poly, ones])
            transformed_poly = points_homogeneous.dot(rot_matrix.T)

            # Recompute enclosing bounding box
            x_min = float(np.min(transformed_poly[:, 0]))
            y_min = float(np.min(transformed_poly[:, 1]))
            x_max = float(np.max(transformed_poly[:, 0]))
            y_max = float(np.max(transformed_poly[:, 1]))

            anno_copy = dict(anno)
            anno_copy["polygon"] = transformed_poly.tolist()
            anno_copy["bbox"] = [x_min, y_min, x_max, y_max]
            anno_copy["skew_applied"] = skew_angle
            updated_annotations.append(anno_copy)

        # 7. Save Degraded Outputs
        out_img_p = Path(output_image_path)
        out_gt_p = Path(output_gt_path)
        out_img_p.parent.mkdir(parents=True, exist_ok=True)
        out_gt_p.parent.mkdir(parents=True, exist_ok=True)

        # Encode with slight JPEG compression artifacts typical of 2000s document archives
        cv2.imwrite(str(out_img_p), degraded, [cv2.IMWRITE_JPEG_QUALITY, 85])

        degraded_gt = dict(gt_data)
        degraded_gt["image_path"] = str(out_img_p.name)
        degraded_gt["skew_angle"] = skew_angle
        degraded_gt["blur_ksize"] = blur_ksize
        degraded_gt["noise_density"] = noise_density
        degraded_gt["annotations"] = updated_annotations

        with open(out_gt_p, "w", encoding="utf-8") as f:
            json.dump(degraded_gt, f, ensure_ascii=False, indent=2)

        return degraded_gt

    def _add_speckle_noise(self, image: np.ndarray, density: float) -> np.ndarray:
        """Adds salt and pepper noise simulating dust on scanner optics."""
        output = image.copy()
        num_salt = int(density * image.shape[0] * image.shape[1] * 0.5)
        num_pepper = int(density * image.shape[0] * image.shape[1] * 0.5)

        # Pepper (dark specks)
        for _ in range(num_pepper):
            y = random.randint(0, image.shape[0] - 1)
            x = random.randint(0, image.shape[1] - 1)
            output[y, x] = [random.randint(10, 60)] * 3

        # Salt (light specks on dark ink)
        for _ in range(num_salt):
            y = random.randint(0, image.shape[0] - 1)
            x = random.randint(0, image.shape[1] - 1)
            output[y, x] = [random.randint(210, 255)] * 3

        return output

    def _add_scanner_crease(self, image: np.ndarray) -> np.ndarray:
        """Adds a faint horizontal/vertical scanning shadow or fold artifact."""
        output = image.copy()
        h, w = image.shape[:2]
        # Add a subtle faint vertical fold line near center
        crease_x = int(w * 0.48)
        cv2.line(output, (crease_x, 0), (crease_x + 8, h), (210, 210, 210), 2)
        return output


if __name__ == "__main__":
    engine = ScanDegradationEngine(seed=42)
    clean_img = "data/output/clean/DRAWING-TEST-001.png"
    clean_gt = "data/output/clean/DRAWING-TEST-001_gt.json"
    deg_img = "data/output/degraded/DRAWING-TEST-001_deg.jpg"
    deg_gt = "data/output/degraded/DRAWING-TEST-001_deg_gt.json"

    result = engine.degrade(clean_img, clean_gt, deg_img, deg_gt, skew_angle=2.2)
    print("Degradation pipeline executed successfully.")
    print(f"Applied skew: {result['skew_angle']} degrees")
    print(f"Degraded image saved to {deg_img}")

