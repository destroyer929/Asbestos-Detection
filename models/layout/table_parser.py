# Copyright (c) 2026 Karunakar (destroyer929). All rights reserved.
# Proprietary & Confidential. Authorized for technical evaluation and portfolio review only.
"""
Finish Schedule (特記仕上表) Table Detection & Cell Structure Parser.
Uses OpenCV morphological line kernels to locate architectural schedule grids,
segments row and column intersections, associates OCR bounding boxes into cells,
and reconstructs structured room-to-finish material specifications.
"""

from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np
import cv2


@dataclass
class TableCell:
    """Represents a single parsed cell in the Finish Schedule grid."""
    row_idx: int
    col_idx: int
    header_name: str
    bbox: List[int]  # [x1, y1, x2, y2]
    text: str = ""
    confidence: float = 1.0


@dataclass
class RoomFinishRecord:
    """Represents the complete finish specifications for one room."""
    room_name: str
    floor_finish: str = ""
    skirting_finish: str = ""
    wall_finish: str = ""
    ceiling_finish: str = ""
    remarks: str = ""
    cells: List[TableCell] = field(default_factory=list)


class FinishScheduleTableParser:
    """Detects and reconstructs tabular relationships from Finish Schedules (仕上表)."""

    DEFAULT_HEADERS = ["室名", "床", "巾木", "壁", "天井", "備考"]

    def __init__(self, min_table_area: int = 50000):
        self.min_table_area = min_table_area

    def detect_table_boundary(self, image: np.ndarray) -> Optional[List[int]]:
        """
        Detects the outer bounding box of the finish schedule table using morphology.
        Returns: [x_min, y_min, x_max, y_max] or None if no table found.
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 25, 10
        )

        h, w = gray.shape[:2]
        scale = max(1, w // 100)
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (scale, 1))
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, scale))

        horiz_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horiz_kernel, iterations=2)
        vert_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vert_kernel, iterations=2)

        table_mask = cv2.add(horiz_lines, vert_lines)

        contours, _ = cv2.findContours(table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        best_box = None
        max_score = 0

        for cnt in contours:
            x, y, cw, ch = cv2.boundingRect(cnt)
            area = cw * ch

            if cw > int(w * 0.85) and ch > int(h * 0.85):
                continue

            # Skip bottom-right Title Block (typically located at x > 40% and y > 60%)
            if x > int(w * 0.40) and y > int(h * 0.60):
                continue

            # Finish schedule tables occupy a moderate vertical portion (never engulfing the whole floor plan)
            if ch > int(h * 0.35):
                continue

            min_cw = int(w * 0.15)
            min_ch = int(h * 0.06)
            if cw >= min_cw and ch >= min_ch and (cw / float(ch)) >= 1.4:
                roi_h = horiz_lines[y:y+ch, x:x+cw]
                roi_v = vert_lines[y:y+ch, x:x+cw]
                grid_density = cv2.countNonZero(roi_h) + cv2.countNonZero(roi_v)
                density_ratio = grid_density / float(area)

                # Require legitimate tabular grid density (filtering out open floor plan rooms)
                if density_ratio < 0.035:
                    continue

                aspect_bonus = min(cw / float(ch), 4.0)
                score = (density_ratio * 1000.0) * (area ** 0.3) * aspect_bonus
                if score > max_score:
                    max_score = score
                    best_box = [x, y, x + cw, y + ch]

        return best_box

    def extract_grid_cells(
        self,
        image: np.ndarray,
        table_bbox: List[int]
    ) -> List[Dict[str, Any]]:
        """
        Segments physical grid cells directly from morphological table grid dividers.
        Returns a structured matrix of cells with bounding boxes and row/column indices.
        """
        tx1, ty1, tx2, ty2 = table_bbox
        table_roi = image[ty1:ty2, tx1:tx2]
        if table_roi.size == 0:
            return []

        if len(table_roi.shape) == 3:
            gray = cv2.cvtColor(table_roi, cv2.COLOR_BGR2GRAY)
        else:
            gray = table_roi.copy()

        bin_inv = (gray < 210).astype(np.uint8) * 255

        # Horizontal divider lines
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(8, table_roi.shape[1] // 20), 1))
        h_lines = cv2.morphologyEx(bin_inv, cv2.MORPH_OPEN, h_kernel)

        # Vertical divider lines
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, table_roi.shape[0] // 20)))
        v_lines = cv2.morphologyEx(bin_inv, cv2.MORPH_OPEN, v_kernel)

        # Find row divider y-coordinates (adaptive to raster DPI/compression)
        h_sums = np.sum(h_lines, axis=1) / 255.0
        row_divs = []
        min_row_gap = max(8, int(table_roi.shape[0] * 0.04))
        for y in range(len(h_sums)):
            if h_sums[y] > (table_roi.shape[1] * 0.12):
                if not row_divs or (y - row_divs[-1]) > min_row_gap:
                    row_divs.append(y)

        # Ensure table top and bottom boundaries are included
        if not row_divs or row_divs[0] > 15:
            row_divs.insert(0, 0)
        if (table_roi.shape[0] - row_divs[-1]) > 15:
            row_divs.append(table_roi.shape[0])

        # Find col divider x-coordinates
        v_sums = np.sum(v_lines, axis=0) / 255.0
        col_divs = []
        min_col_gap = max(14, int(table_roi.shape[1] * 0.035))
        for x in range(len(v_sums)):
            if v_sums[x] > (table_roi.shape[0] * 0.12):
                if not col_divs or (x - col_divs[-1]) > min_col_gap:
                    col_divs.append(x)

        # Ensure table left and right boundaries are included
        if not col_divs or col_divs[0] > 15:
            col_divs.insert(0, 0)
        if (table_roi.shape[1] - col_divs[-1]) > 15:
            col_divs.append(table_roi.shape[1])

        standard_headers = ["室名", "床", "巾木", "壁", "天井", "備考"]
        cells = []

        for r_idx in range(len(row_divs) - 1):
            r_y1 = row_divs[r_idx]
            r_y2 = row_divs[r_idx + 1]
            for c_idx in range(len(col_divs) - 1):
                c_x1 = col_divs[c_idx]
                c_x2 = col_divs[c_idx + 1]

                global_bbox = [tx1 + c_x1, ty1 + r_y1, tx1 + c_x2, ty1 + r_y2]
                col_name = standard_headers[c_idx] if c_idx < len(standard_headers) else f"Col_{c_idx}"

                cells.append({
                    "row_idx": r_idx,
                    "col_idx": c_idx,
                    "header_name": col_name,
                    "bbox": global_bbox,
                    "is_header_row": r_idx == 0
                })

        return cells

    def parse_schedule_cells(
        self,
        table_bbox: List[int],
        detected_texts: List[Dict[str, Any]],
        expected_cols: int = 6,
        image: Optional[np.ndarray] = None
    ) -> List[RoomFinishRecord]:
        """
        Groups detected text items into grid rows and columns based on spatial coordinates.
        Supports direct physical cell assignment when image is provided, with anchor-based fallback.
        """
        tx1, ty1, tx2, ty2 = table_bbox

        table_texts = []
        for item in detected_texts:
            bbox = item["bbox"]
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0
            if tx1 <= cx <= tx2 and ty1 <= cy <= ty2:
                table_texts.append(item)

        if not table_texts:
            return []

        # 1. High-fidelity physical grid mapping if image array is available
        if image is not None:
            cells = self.extract_grid_cells(image, table_bbox)
            if len(cells) >= 12:
                grid: Dict[Tuple[int, int], List[str]] = {}
                header_names: Dict[int, str] = {}

                for c in cells:
                    r_idx, c_idx = c["row_idx"], c["col_idx"]
                    if c_idx not in header_names and c.get("header_name"):
                        header_names[c_idx] = c["header_name"]
                    cx1, cy1, cx2, cy2 = c["bbox"]
                    for it in table_texts:
                        bx1, by1, bx2, by2 = it["bbox"]
                        cen_x = (bx1 + bx2) / 2.0
                        cen_y = (by1 + by2) / 2.0
                        if cx1 <= cen_x <= cx2 and cy1 <= cen_y <= cy2:
                            grid.setdefault((r_idx, c_idx), []).append(it["text"])

                max_r = max(c["row_idx"] for c in cells)
                max_c = max(c["col_idx"] for c in cells)

                # Determine which row is the column header row (e.g. contains 室名, 床, 巾木, 壁, 天井, 備考)
                header_r = -1
                for r in range(min(3, max_r + 1)):
                    row_r_texts = " ".join([t for c_idx in range(max_c + 1) for t in grid.get((r, c_idx), [])])
                    match_count = sum(1 for k in ["室名", "床", "巾木", "壁", "天井", "備考", "FL", "WALL", "CEILING"] if k in row_r_texts)
                    if match_count >= 2:
                        header_r = r
                        break

                start_r = header_r + 1 if header_r >= 0 else (1 if max_r >= 1 else 0)

                records: List[RoomFinishRecord] = []
                for r in range(start_r, max_r + 1):
                    row_cells: List[TableCell] = []
                    for c_idx in range(max_c + 1):
                        cell_bbox = next((c["bbox"] for c in cells if c["row_idx"] == r and c["col_idx"] == c_idx), table_bbox)
                        col_h = header_names.get(c_idx, f"Col_{c_idx}")
                        cell_text = " ".join(grid.get((r, c_idx), []))
                        row_cells.append(
                            TableCell(
                                row_idx=r - start_r,
                                col_idx=c_idx,
                                header_name=col_h,
                                bbox=cell_bbox,
                                text=cell_text,
                                confidence=1.0
                            )
                        )

                    room_name = row_cells[0].text if len(row_cells) > 0 and row_cells[0].text.strip() else f"Room_{r}"
                    floor = row_cells[1].text if len(row_cells) > 1 else ""
                    skirting = row_cells[2].text if len(row_cells) > 2 else ""
                    wall = row_cells[3].text if len(row_cells) > 3 else ""
                    ceiling = row_cells[4].text if len(row_cells) > 4 else ""
                    remarks = row_cells[5].text if len(row_cells) > 5 else ""

                    if any([room_name.strip(), floor.strip(), wall.strip(), ceiling.strip(), remarks.strip()]):
                        records.append(
                            RoomFinishRecord(
                                room_name=room_name,
                                floor_finish=floor,
                                skirting_finish=skirting,
                                wall_finish=wall,
                                ceiling_finish=ceiling,
                                remarks=remarks,
                                cells=row_cells
                            )
                        )
                if records:
                    return records

        # 2. Adaptive anchor-based row clustering fallback
        sorted_by_y = sorted(table_texts, key=lambda t: (t["bbox"][1] + t["bbox"][3]) / 2.0)
        table_h = ty2 - ty1
        row_height_tol = max(20.0, table_h * 0.065)

        row_clusters: List[List[Dict[str, Any]]] = []
        current_cluster: List[Dict[str, Any]] = [sorted_by_y[0]]
        anchor_y = (sorted_by_y[0]["bbox"][1] + sorted_by_y[0]["bbox"][3]) / 2.0

        for item in sorted_by_y[1:]:
            curr_y = (item["bbox"][1] + item["bbox"][3]) / 2.0
            if abs(curr_y - anchor_y) < row_height_tol:
                current_cluster.append(item)
            else:
                row_clusters.append(current_cluster)
                current_cluster = [item]
                anchor_y = curr_y

        if current_cluster:
            row_clusters.append(current_cluster)

        header_row = sorted(row_clusters[0], key=lambda t: t["bbox"][0])
        headers = [h["text"] for h in header_row]

        data_rows = row_clusters[1:]
        records: List[RoomFinishRecord] = []

        for r_idx, row_items in enumerate(data_rows):
            sorted_row = sorted(row_items, key=lambda t: t["bbox"][0])

            row_cells: List[TableCell] = []
            for c_idx, cell_item in enumerate(sorted_row):
                h_name = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
                row_cells.append(
                    TableCell(
                        row_idx=r_idx,
                        col_idx=c_idx,
                        header_name=h_name,
                        bbox=cell_item["bbox"],
                        text=cell_item["text"],
                        confidence=cell_item.get("confidence", 1.0)
                    )
                )

            room_name = row_cells[0].text if len(row_cells) > 0 else f"Room_{r_idx + 1}"
            floor = row_cells[1].text if len(row_cells) > 1 else ""
            skirting = row_cells[2].text if len(row_cells) > 2 else ""
            wall = row_cells[3].text if len(row_cells) > 3 else ""
            ceiling = row_cells[4].text if len(row_cells) > 4 else ""
            remarks = row_cells[5].text if len(row_cells) > 5 else ""

            records.append(
                RoomFinishRecord(
                    room_name=room_name,
                    floor_finish=floor,
                    skirting_finish=skirting,
                    wall_finish=wall,
                    ceiling_finish=ceiling,
                    remarks=remarks,
                    cells=row_cells
                )
            )

        return records

