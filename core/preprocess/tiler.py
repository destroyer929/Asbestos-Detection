"""
Sliding-Window Overlapping Tiler & Boundary Stitcher for Large-Scale Blueprints.
Enables high-resolution text detection on massive A0/A1 engineering drawings without
downsampling loss or GPU Out-Of-Memory (OOM) failures.
Includes global coordinate translation, Non-Maximum Suppression (NMS), and box merging.
"""

from __future__ import annotations
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
import numpy as np


@dataclass
class ImageTile:
    """Represents a single cropped tile from a large architectural drawing."""
    tile_id: int
    image: np.ndarray
    x_offset: int
    y_offset: int
    width: int
    height: int


@dataclass
class DetectedBox:
    """Represents a text box with global sheet coordinates."""
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    confidence: float
    text: str = ""
    tile_id: int = -1


class LargeSheetTiler:
    """Cuts large blueprints into overlapping tiles and stitches detections back."""

    def __init__(
        self,
        tile_size: int = 1024,
        overlap_ratio: float = 0.20,
        nms_iou_threshold: float = 0.45
    ):
        self.tile_size = tile_size
        self.overlap_ratio = overlap_ratio
        self.nms_iou_threshold = nms_iou_threshold
        self.step_size = int(tile_size * (1.0 - overlap_ratio))

    def tile_image(self, image: np.ndarray) -> List[ImageTile]:
        """
        Slices a full-scale blueprint into overlapping tiles.
        Pads boundary tiles with white background to maintain uniform size.
        """
        h, w = image.shape[:2]

        # If drawing is already smaller than tile size, return as single tile
        if h <= self.tile_size and w <= self.tile_size:
            return [
                ImageTile(
                    tile_id=0,
                    image=image.copy(),
                    x_offset=0,
                    y_offset=0,
                    width=w,
                    height=h
                )
            ]

        tiles: List[ImageTile] = []
        tile_id = 0

        y = 0
        while y < h:
            x = 0
            tile_h = min(self.tile_size, h - y)

            while x < w:
                tile_w = min(self.tile_size, w - x)

                # Crop tile
                crop = image[y : y + tile_h, x : x + tile_w]

                # If crop is smaller than tile_size, pad with white (255)
                if tile_h < self.tile_size or tile_w < self.tile_size:
                    if len(image.shape) == 3:
                        padded = np.full((self.tile_size, self.tile_size, image.shape[2]), 255, dtype=image.dtype)
                        padded[0:tile_h, 0:tile_w, :] = crop
                    else:
                        padded = np.full((self.tile_size, self.tile_size), 255, dtype=image.dtype)
                        padded[0:tile_h, 0:tile_w] = crop
                    tile_img = padded
                else:
                    tile_img = crop

                tiles.append(
                    ImageTile(
                        tile_id=tile_id,
                        image=tile_img,
                        x_offset=x,
                        y_offset=y,
                        width=tile_w,
                        height=tile_h
                    )
                )
                tile_id += 1

                if x + self.tile_size >= w:
                    break
                x += self.step_size

            if y + self.tile_size >= h:
                break
            y += self.step_size

        return tiles

    def stitch_detections(
        self,
        tile_detections: List[Tuple[ImageTile, List[DetectedBox]]]
    ) -> List[DetectedBox]:
        """
        Transforms tile-local detections back to global sheet coordinates
        and eliminates duplicates using Non-Maximum Suppression (NMS).
        """
        global_boxes: List[DetectedBox] = []

        for tile, boxes in tile_detections:
            for b in boxes:
                # Local coords -> Global coords
                gx1 = b.bbox[0] + tile.x_offset
                gy1 = b.bbox[1] + tile.y_offset
                gx2 = b.bbox[2] + tile.x_offset
                gy2 = b.bbox[3] + tile.y_offset

                global_boxes.append(
                    DetectedBox(
                        bbox=[gx1, gy1, gx2, gy2],
                        confidence=b.confidence,
                        text=b.text,
                        tile_id=tile.tile_id
                    )
                )

        if not global_boxes:
            return []

        # Run Non-Maximum Suppression (NMS)
        return self._apply_nms(global_boxes, self.nms_iou_threshold)

    def _apply_nms(self, boxes: List[DetectedBox], iou_thresh: float) -> List[DetectedBox]:
        """Performs Non-Maximum Suppression to merge duplicate boxes at tile borders."""
        if len(boxes) == 0:
            return []

        # Sort by confidence descending
        sorted_boxes = sorted(boxes, key=lambda b: b.confidence, reverse=True)
        selected: List[DetectedBox] = []

        while sorted_boxes:
            current = sorted_boxes.pop(0)
            selected.append(current)

            remaining = []
            for candidate in sorted_boxes:
                iou = self._calculate_iou(current.bbox, candidate.bbox)
                if iou < iou_thresh:
                    remaining.append(candidate)
                else:
                    # If overlapping significantly, union the boxes if candidate has text
                    if candidate.text and not current.text:
                        current.text = candidate.text
            sorted_boxes = remaining

        return selected

    @staticmethod
    def _calculate_iou(boxA: List[float], boxB: List[float]) -> float:
        """Calculates Intersection over Union (IoU) of two bounding boxes."""
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
        if interArea == 0.0:
            return 0.0

        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

        iou = interArea / float(boxAArea + boxBArea - interArea)
        return iou


if __name__ == "__main__":
    tiler = LargeSheetTiler(tile_size=1024, overlap_ratio=0.2)
    # Test on a large dummy canvas
    dummy_blueprint = np.zeros((3000, 4500, 3), dtype=np.uint8)
    tiles = tiler.tile_image(dummy_blueprint)
    print(f"Tiler created {len(tiles)} overlapping tiles from 3000x4500 drawing.")

    # Test coordinate stitching with synthetic overlapping boxes
    t0 = tiles[0]
    t1 = tiles[1]
    box0 = DetectedBox(bbox=[800, 200, 950, 240], confidence=0.95, text="吹付けロックウール")
    box1 = DetectedBox(bbox=[800 - t1.x_offset, 200, 950 - t1.x_offset, 240], confidence=0.88, text="吹付けロックウール")

    stitched = tiler.stitch_detections([(t0, [box0]), (t1, [box1])])
    print(f"Stitched duplicate detections across tile borders: 2 candidate boxes -> {len(stitched)} merged box.")
    print(f"Final box coordinates: {stitched[0].bbox}")

