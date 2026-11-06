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

            min_cw = int(w * 0.18)
            min_ch = int(h * 0.08)
            if cw >= min_cw and ch >= min_ch and (cw / float(ch)) >= 1.35:
                roi_h = horiz_lines[y:y+ch, x:x+cw]
                roi_v = vert_lines[y:y+ch, x:x+cw]
                grid_density = cv2.countNonZero(roi_h) + cv2.countNonZero(roi_v)

                score = area * 0.4 + grid_density * 0.6
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
        expected_cols: int = 6
    ) -> List[RoomFinishRecord]:
        """
        Groups detected text items into grid rows and columns based on spatial coordinates.
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

        sorted_by_y = sorted(table_texts, key=lambda t: (t["bbox"][1] + t["bbox"][3]) / 2.0)

        row_clusters: List[List[Dict[str, Any]]] = []
        current_cluster: List[Dict[str, Any]] = [sorted_by_y[0]]

        for item in sorted_by_y[1:]:
            curr_y = (item["bbox"][1] + item["bbox"][3]) / 2.0
            prev_y = (current_cluster[-1]["bbox"][1] + current_cluster[-1]["bbox"][3]) / 2.0
            if abs(curr_y - prev_y) < 25:
                current_cluster.append(item)
            else:
                row_clusters.append(current_cluster)
                current_cluster = [item]

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

