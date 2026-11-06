"""
Synthetic Architectural CAD Drawing Generator for Asbestos OCR & Diagnostics.
Generates authentic Japanese engineering blueprints using ezdxf for CAD structure
and renders high-resolution raster images with pixel-accurate ground-truth annotations.
"""

from __future__ import annotations
import os
import math
import json
import random
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from PIL import Image, ImageDraw, ImageFont
import ezdxf

from data.database.db_manager import MaterialsDatabase, MaterialEntry
from data.generator.vocabulary import (
    ROOM_NAMES_JA,
    FINISH_SCHEDULE_HEADERS,
    DIMENSION_STRINGS,
    DRAWING_BLOCK_LABELS,
    THICKNESS_MODIFIERS,
    FINISH_MODIFIERS
)


class CADBlueprintGenerator:
    """Generates synthetic architectural drawings with paired CAD DXF, images, and labels."""

    def __init__(
        self,
        db: Optional[MaterialsDatabase] = None,
        font_path: str = "C:/Windows/Fonts/msgothic.ttc",
        width: int = 2400,
        height: int = 1600
    ):
        self.db = db or MaterialsDatabase()
        self.font_path = font_path if os.path.exists(font_path) else "C:/Windows/Fonts/GOTHIC.TTF"
        self.width = width
        self.height = height

        # Load fonts at various scales
        self.fonts = {
            "title": self._load_font(28),
            "header": self._load_font(20),
            "body": self._load_font(16),
            "annotation": self._load_font(15),
            "dimension": self._load_font(13),
            "small": self._load_font(12)
        }

    def _load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        try:
            return ImageFont.truetype(self.font_path, size)
        except Exception:
            return ImageFont.load_default()

    def generate(
        self,
        drawing_id: str,
        output_dir: Path | str,
        seed: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Creates a complete synthetic drawing set:
        1. .dxf CAD vector file
        2. .png high-resolution rendered image
        3. .json ground-truth annotation file with pixel coordinates and asbestos tags
        """
        if seed is not None:
            random.seed(seed)

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # 1. Initialize DXF Document
        doc = ezdxf.new("R2010")
        msp = doc.modelspace()
        self._setup_dxf_layers(doc)

        # 2. Setup Raster Drawing Canvas
        img = Image.new("RGB", (self.width, self.height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        annotations: List[Dict[str, Any]] = []

        # 3. Draw Outer Border and Title Block
        self._draw_border_and_title(draw, msp, annotations, drawing_id)

        # 4. Draw Floorplan Geometry (Walls, Columns, Doors, Dimensions)
        room_boxes = self._draw_floorplan_geometry(draw, msp, annotations)

        # 5. Draw Finish Schedule Table (仕上表)
        self._draw_finish_schedule(draw, msp, annotations, room_boxes)

        # 6. Draw Callout Leader Annotations with Mixed Orientations
        self._draw_material_callouts(draw, msp, annotations, room_boxes)

        # 7. Save Artifacts
        dxf_file = out_path / f"{drawing_id}.dxf"
        png_file = out_path / f"{drawing_id}.png"
        json_file = out_path / f"{drawing_id}_gt.json"

        doc.saveas(dxf_file)
        img.save(png_file, dpi=(200, 200))

        ground_truth = {
            "drawing_id": drawing_id,
            "image_path": str(png_file.name),
            "dxf_path": str(dxf_file.name),
            "dimensions": {"width": self.width, "height": self.height},
            "annotation_count": len(annotations),
            "asbestos_positive_count": sum(1 for a in annotations if a["asbestos_status"] == "POSITIVE"),
            "non_asbestos_count": sum(1 for a in annotations if a["asbestos_status"] == "NEGATIVE"),
            "annotations": annotations
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(ground_truth, f, ensure_ascii=False, indent=2)

        return ground_truth

    def _setup_dxf_layers(self, doc: ezdxf.document.Drawing) -> None:
        """Sets up industry-standard CAD layers."""
        layers = [
            ("A-WALL", 7),       # White/Black, continuous
            ("A-COL", 1),        # Red
            ("A-DOOR", 3),       # Green
            ("A-DIM", 4),        # Cyan
            ("A-ANNO", 2),       # Yellow
            ("A-TABLE", 7),      # White/Black
            ("A-TITLE", 7)       # White/Black
        ]
        for name, color in layers:
            if name not in doc.layers:
                doc.layers.add(name, color=color)

    def _draw_border_and_title(
        self,
        draw: ImageDraw.ImageDraw,
        msp: Any,
        annotations: List[Dict[str, Any]],
        drawing_id: str
    ) -> None:
        """Draws outer blueprint margin, grid ticks, and Japanese title block."""
        margin = 40
        w, h = self.width, self.height

        # Outer double border
        draw.rectangle([margin, margin, w - margin, h - margin], outline=(0, 0, 0), width=3)
        draw.rectangle([margin + 8, margin + 8, w - margin - 8, h - margin - 8], outline=(0, 0, 0), width=1)
        msp.add_lwpolyline([(margin, margin), (w - margin, margin), (w - margin, h - margin), (margin, h - margin), (margin, margin)], dxfattribs={"layer": "A-TITLE"})

        # Title Block in bottom right corner
        tb_w, tb_h = 580, 200
        tb_x1, tb_y1 = w - margin - 8 - tb_w, h - margin - 8 - tb_h
        tb_x2, tb_y2 = w - margin - 8, h - margin - 8

        draw.rectangle([tb_x1, tb_y1, tb_x2, tb_y2], outline=(0, 0, 0), width=2)
        draw.line([tb_x1, tb_y1 + 45, tb_x2, tb_y1 + 45], fill=(0, 0, 0), width=1)
        draw.line([tb_x1, tb_y1 + 90, tb_x2, tb_y1 + 90], fill=(0, 0, 0), width=1)
        draw.line([tb_x1, tb_y1 + 145, tb_x2, tb_y1 + 145], fill=(0, 0, 0), width=1)
        draw.line([tb_x1 + 180, tb_y1 + 90, tb_x1 + 180, tb_y2], fill=(0, 0, 0), width=1)

        # Title block text strings
        items = [
            ("工事名称: アルフレッド浜松事業所 耐震改修設計", (tb_x1 + 10, tb_y1 + 12), "header", "title_block"),
            ("図面名称: 平面詳細図・特記仕上表", (tb_x1 + 10, tb_y1 + 55), "header", "title_block"),
            ("設計: Alfred R&D Architectural Labs", (tb_x1 + 10, tb_y1 + 105), "body", "title_block"),
            ("作成年月: 1982年 (昭和57年) 8月", (tb_x1 + 10, tb_y1 + 160), "body", "title_block"),
            (f"図面番号: {drawing_id}", (tb_x1 + 200, tb_y1 + 105), "body", "title_block"),
            ("縮尺: 1/100 (A1) 1/200 (A3)", (tb_x1 + 200, tb_y1 + 160), "body", "title_block")
        ]

        for text, (x, y), font_key, r_type in items:
            font = self.fonts[font_key]
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((x, y), text, fill=(0, 0, 0), font=font)
            annotations.append({
                "text": text,
                "bbox": [x, y, x + tw, y + th],
                "polygon": [[x, y], [x + tw, y], [x + tw, y + th], [x, y + th]],
                "angle": 0,
                "region_type": r_type,
                "asbestos_status": "NONE",
                "hazard_level": "NONE",
                "matched_material_id": None
            })

    def _draw_floorplan_geometry(
        self,
        draw: ImageDraw.ImageDraw,
        msp: Any,
        annotations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Draws architectural rooms, partition walls, columns, and dimensions."""
        margin = 40
        table_w = 830
        tx1 = max(self.width - margin - 20 - table_w, 1000)

        plan_x = margin + 40
        plan_y = 130
        plan_w = max(tx1 - plan_x - 50, 700)
        plan_h = self.height - plan_y - 230

        # Outer walls
        draw.rectangle([plan_x, plan_y, plan_x + plan_w, plan_y + plan_h], outline=(0, 0, 0), width=4)
        draw.rectangle([plan_x + 8, plan_y + 8, plan_x + plan_w - 8, plan_y + plan_h - 8], outline=(0, 0, 0), width=2)

        # Subdivide into 6 proportional rooms
        w1 = int(plan_w * 0.33)
        w2 = int(plan_w * 0.66)
        h_mid = int(plan_h * 0.48)

        r1 = {"name": "機械室", "rect": [plan_x, plan_y, plan_x + w1, plan_y + h_mid], "has_spray": True}
        r2 = {"name": "ボイラー室", "rect": [plan_x + w1, plan_y, plan_x + w2, plan_y + h_mid], "has_pipe_insul": True}
        r3 = {"name": "倉庫 (1)", "rect": [plan_x + w2, plan_y, plan_x + plan_w, plan_y + h_mid], "has_slate": True}
        r4 = {"name": "事務室 (A)", "rect": [plan_x, plan_y + h_mid, plan_x + int(plan_w * 0.52), plan_y + plan_h], "has_vinyl_tile": True}
        r5 = {"name": "給湯室", "rect": [plan_x + int(plan_w * 0.52), plan_y + h_mid, plan_x + int(plan_w * 0.72), plan_y + plan_h], "has_calsil": True}
        r6 = {"name": "廊下・ホール", "rect": [plan_x + int(plan_w * 0.72), plan_y + h_mid, plan_x + plan_w, plan_y + plan_h], "has_vinyl_tile": True}

        rooms = [r1, r2, r3, r4, r5, r6]

        # Draw interior dividing walls
        for r in rooms:
            rx1, ry1, rx2, ry2 = r["rect"]
            draw.rectangle([rx1, ry1, rx2, ry2], outline=(0, 0, 0), width=3)

            # Room center label
            cx = (rx1 + rx2) // 2
            cy = (ry1 + ry2) // 2
            r_name = r["name"]
            font = self.fonts["header"]
            bbox = font.getbbox(r_name)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((cx - tw // 2, cy - th // 2), r_name, fill=(20, 20, 20), font=font)
            annotations.append({
                "text": r_name,
                "bbox": [cx - tw // 2, cy - th // 2, cx + tw // 2, cy + th // 2],
                "polygon": [[cx - tw // 2, cy - th // 2], [cx + tw // 2, cy - th // 2], [cx + tw // 2, cy + th // 2], [cx - tw // 2, cy + th // 2]],
                "angle": 0,
                "region_type": "room_label",
                "asbestos_status": "NONE",
                "hazard_level": "NONE",
                "matched_material_id": None
            })

            # Add floor level dimension e.g. FL ±0
            fl_text = "FL ±0"
            dfont = self.fonts["small"]
            dbbox = dfont.getbbox(fl_text)
            dtw = dbbox[2] - dbbox[0]
            dth = dbbox[3] - dbbox[1]
            draw.text((cx - dtw // 2, cy + 22), fl_text, fill=(80, 80, 80), font=dfont)
            annotations.append({
                "text": fl_text,
                "bbox": [cx - dtw // 2, cy + 22, cx + dtw // 2, cy + 22 + dth],
                "polygon": [[cx - dtw // 2, cy + 22], [cx + dtw // 2, cy + 22], [cx + dtw // 2, cy + 22 + dth], [cx - dtw // 2, cy + 22 + dth]],
                "angle": 0,
                "region_type": "dimension",
                "asbestos_status": "NONE",
                "hazard_level": "NONE",
                "matched_material_id": None
            })

        # Draw structural reinforced concrete columns (RC造 柱) at grid corners
        col_coords = [
            (plan_x, plan_y), (plan_x + w1, plan_y), (plan_x + w2, plan_y), (plan_x + plan_w, plan_y),
            (plan_x, plan_y + h_mid), (plan_x + w1, plan_y + h_mid), (plan_x + w2, plan_y + h_mid), (plan_x + plan_w, plan_y + h_mid),
            (plan_x, plan_y + plan_h), (plan_x + int(plan_w * 0.52), plan_y + plan_h), (plan_x + plan_w, plan_y + plan_h)
        ]
        cw = 24
        for cx, cy in col_coords:
            draw.rectangle([cx - cw // 2, cy - cw // 2, cx + cw // 2, cy + cw // 2], fill=(40, 40, 40), outline=(0, 0, 0), width=1)
            # Cross hatch
            draw.line([cx - cw // 2, cy - cw // 2, cx + cw // 2, cy + cw // 2], fill=(255, 255, 255), width=1)
            draw.line([cx - cw // 2, cy + cw // 2, cx + cw // 2, cy - cw // 2], fill=(255, 255, 255), width=1)

        # Draw outer architectural dimensions and grid marks
        self._draw_dimension_lines(draw, annotations, plan_x, plan_y, plan_w, plan_h, w1, w2)

        return rooms

    def _draw_dimension_lines(
        self,
        draw: ImageDraw.ImageDraw,
        annotations: List[Dict[str, Any]],
        px: int, py: int, pw: int, ph: int,
        w1: int, w2: int
    ) -> None:
        """Draws dimension extension lines and dimension values."""
        dim_y = py - 40
        draw.line([px, dim_y, px + pw, dim_y], fill=(0, 0, 0), width=1)
        draw.line([px, py - 60, px, py - 10], fill=(0, 0, 0), width=1)
        draw.line([px + w1, py - 60, px + w1, py - 10], fill=(0, 0, 0), width=1)
        draw.line([px + w2, py - 60, px + w2, py - 10], fill=(0, 0, 0), width=1)
        draw.line([px + pw, py - 60, px + pw, py - 10], fill=(0, 0, 0), width=1)

        dims = [
            ("4,500", (px + w1 // 2, dim_y - 18)),
            ("4,500", (px + (w1 + w2) // 2, dim_y - 18)),
            ("4,500", (px + (w2 + pw) // 2, dim_y - 18)),
            ("13,500", (px + pw // 2, dim_y - 45))
        ]
        draw.line([px, dim_y - 25, px + pw, dim_y - 25], fill=(0, 0, 0), width=1)

        for text, (x, y) in dims:
            font = self.fonts["dimension"]
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text((x - tw // 2, y), text, fill=(0, 0, 0), font=font)
            annotations.append({
                "text": text,
                "bbox": [x - tw // 2, y, x + tw // 2, y + th],
                "polygon": [[x - tw // 2, y], [x + tw // 2, y], [x + tw // 2, y + th], [x - tw // 2, y + th]],
                "angle": 0,
                "region_type": "dimension",
                "asbestos_status": "NONE",
                "hazard_level": "NONE",
                "matched_material_id": None
            })

    def _draw_finish_schedule(
        self,
        draw: ImageDraw.ImageDraw,
        msp: Any,
        annotations: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]]
    ) -> None:
        """Draws the structured Finish Schedule table (仕上表) on the right side."""
        margin = 40
        col_widths = [140, 150, 120, 160, 180, 80]  # Room, Floor, Skirting, Wall, Ceiling, Remarks
        table_w = sum(col_widths)
        tx1 = max(self.width - margin - 20 - table_w, 1000)
        ty1 = 100
        row_h = 42
        headers = ["室名", "床 (FL)", "巾木", "壁 (WALL)", "天井 (CEILING)", "備考"]

        # Table Title Header
        title_text = "特記仕上表 (FINISH SCHEDULE)"
        font_title = self.fonts["header"]
        draw.text((tx1 + 10, ty1 - 32), title_text, fill=(0, 0, 0), font=font_title)
        t_bbox = font_title.getbbox(title_text)
        annotations.append({
            "text": title_text,
            "bbox": [tx1 + 10, ty1 - 32, tx1 + 10 + t_bbox[2] - t_bbox[0], ty1 - 32 + t_bbox[3] - t_bbox[1]],
            "polygon": [[tx1 + 10, ty1 - 32], [tx1 + 10 + t_bbox[2] - t_bbox[0], ty1 - 32], [tx1 + 10 + t_bbox[2] - t_bbox[0], ty1 - 32 + t_bbox[3] - t_bbox[1]], [tx1 + 10, ty1 - 32 + t_bbox[3] - t_bbox[1]]],
            "angle": 0,
            "region_type": "table_cell",
            "asbestos_status": "NONE",
            "hazard_level": "NONE",
            "matched_material_id": None
        })

        # Draw Table Outer Outline
        total_rows = len(rooms) + 1
        table_h = total_rows * row_h
        draw.rectangle([tx1, ty1, tx1 + table_w, ty1 + table_h], outline=(0, 0, 0), width=2)

        # Draw Header Row Background
        draw.rectangle([tx1, ty1, tx1 + table_w, ty1 + row_h], fill=(235, 235, 235), outline=(0, 0, 0), width=2)

        # Draw Header Texts and Column Vertical Lines
        curr_x = tx1
        for i, (h_text, cw) in enumerate(zip(headers, col_widths)):
            draw.line([curr_x, ty1, curr_x, ty1 + table_h], fill=(0, 0, 0), width=1 if i > 0 else 2)
            h_font = self.fonts["body"]
            h_bbox = h_font.getbbox(h_text)
            draw.text((curr_x + 8, ty1 + 12), h_text, fill=(0, 0, 0), font=h_font)
            annotations.append({
                "text": h_text,
                "bbox": [curr_x + 8, ty1 + 12, curr_x + 8 + h_bbox[2] - h_bbox[0], ty1 + 12 + h_bbox[3] - h_bbox[1]],
                "polygon": [[curr_x + 8, ty1 + 12], [curr_x + 8 + h_bbox[2] - h_bbox[0], ty1 + 12], [curr_x + 8 + h_bbox[2] - h_bbox[0], ty1 + 12 + h_bbox[3] - h_bbox[1]], [curr_x + 8, ty1 + 12 + h_bbox[3] - h_bbox[1]]],
                "angle": 0,
                "region_type": "table_cell",
                "asbestos_status": "NONE",
                "hazard_level": "NONE",
                "matched_material_id": None
            })
            curr_x += cw

        # Schedule Row Data mapped to MLIT Materials
        schedule_rows = [
            # Room 1: 機械室 -> Friable Level 1 Spray Asbestos
            [
                ("機械室", "NONE", "NONE", None),
                ("モルタル金ゴテ", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-005"),
                ("モルタル H=100", "NONE", "NONE", None),
                ("けい酸カルシウム板第1種 t=8", "POSITIVE", "LEVEL_3", "MAT-L3-002"),
                ("吹付けロックウール t=25", "POSITIVE", "LEVEL_1", "MAT-L1-002"),
                ("耐火被覆", "NONE", "NONE", None)
            ],
            # Room 2: ボイラー室 -> High Friability Level 2 Pipe Insulation
            [
                ("ボイラー室", "NONE", "NONE", None),
                ("コンクリート直押え", "NONE", "NONE", None),
                ("木製巾木 H=60", "NONE", "NONE", None),
                ("石膏ボード t=12.5", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-002"),
                ("石綿保温材 (配管部)", "POSITIVE", "LEVEL_2", "MAT-L2-001"),
                ("保温要", "NONE", "NONE", None)
            ],
            # Room 3: 倉庫 -> Level 3 Slate Corrugated Sheet
            [
                ("倉庫 (1)", "NONE", "NONE", None),
                ("防塵塗料仕上げ", "NONE", "NONE", None),
                ("なし", "NONE", "NONE", None),
                ("スレート波板 t=6.3", "POSITIVE", "LEVEL_3", "MAT-L3-001"),
                ("グラスウール保温材 t=50", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-001"),
                ("外壁側", "NONE", "NONE", None)
            ],
            # Room 4: 事務室 -> Level 3 Vinyl Floor Tile & Acoustic Ceiling
            [
                ("事務室 (A)", "NONE", "NONE", None),
                ("ビニル床タイル 300x300", "POSITIVE", "LEVEL_3", "MAT-L3-003"),
                ("ビニル巾木 H=60", "NONE", "NONE", None),
                ("プラスターボード t=9.5", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-002"),
                ("岩綿吸音板 t=12", "POSITIVE", "LEVEL_3", "MAT-L3-005"),
                ("一般部", "NONE", "NONE", None)
            ],
            # Room 5: 給湯室 -> Safe Non-asbestos CalSil Type 2 + Safe Tiles
            [
                ("給湯室", "NONE", "NONE", None),
                ("磁器質タイル 150角", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-005"),
                ("タイル巾木", "NONE", "NONE", None),
                ("けい酸カルシウム板第2種 t=6", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-003"),
                ("石膏ボード t=9.5 VP", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-002"),
                ("耐水", "NONE", "NONE", None)
            ],
            # Room 6: 廊下 -> Safe Non-asbestos
            [
                ("廊下・ホール", "NONE", "NONE", None),
                ("Pタイル t=2.0", "POSITIVE", "LEVEL_3", "MAT-L3-003"),
                ("木製巾木 H=60", "NONE", "NONE", None),
                ("せっこうボード t=12.5", "NEGATIVE", "NON_ASBESTOS", "MAT-SAFE-002"),
                ("ロックウール吸音板 t=15", "POSITIVE", "LEVEL_3", "MAT-L3-005"),
                ("防音仕様", "NONE", "NONE", None)
            ]
        ]

        # Draw Table Content Rows
        curr_y = ty1 + row_h
        for row_idx, row_cells in enumerate(schedule_rows):
            draw.line([tx1, curr_y, tx1 + table_w, curr_y], fill=(0, 0, 0), width=1)
            cell_x = tx1
            for col_idx, (c_text, status, hazard, mat_id) in enumerate(row_cells):
                font = self.fonts["annotation"]
                c_bbox = font.getbbox(c_text)
                draw.text((cell_x + 6, curr_y + 11), c_text, fill=(10, 10, 10), font=font)
                annotations.append({
                    "text": c_text,
                    "bbox": [cell_x + 6, curr_y + 11, cell_x + 6 + c_bbox[2] - c_bbox[0], curr_y + 11 + c_bbox[3] - c_bbox[1]],
                    "polygon": [[cell_x + 6, curr_y + 11], [cell_x + 6 + c_bbox[2] - c_bbox[0], curr_y + 11], [cell_x + 6 + c_bbox[2] - c_bbox[0], curr_y + 11 + c_bbox[3] - c_bbox[1]], [cell_x + 6, curr_y + 11 + c_bbox[3] - c_bbox[1]]],
                    "angle": 0,
                    "region_type": "table_cell",
                    "asbestos_status": status,
                    "hazard_level": hazard,
                    "matched_material_id": mat_id
                })
                cell_x += col_widths[col_idx]
            curr_y += row_h

    def _draw_material_callouts(
        self,
        draw: ImageDraw.ImageDraw,
        msp: Any,
        annotations: List[Dict[str, Any]],
        rooms: List[Dict[str, Any]]
    ) -> None:
        """
        Draws realistic callout leader lines pointing to walls/beams with mixed orientations:
        Horizontal, 90-degree rotated, and vertical (Tategaki).
        """
        r1, r2, r3, r4, r5, r6 = rooms

        callouts = [
            # 1. Level 1 Sprayed Rockwool on Steel Beam (Mechanical Room)
            {
                "text": "鉄骨梁: 吹付けロックウール t=25 (耐火被覆)",
                "target": (r1["rect"][0] + 80, r1["rect"][1] + 60),
                "elbow": (r1["rect"][0] + 40, r1["rect"][1] + 120),
                "text_pos": (r1["rect"][0] + 10, r1["rect"][1] + 120),
                "angle": 0,
                "asbestos_status": "POSITIVE",
                "hazard_level": "LEVEL_1",
                "matched_material_id": "MAT-L1-002"
            },
            # 2. Level 2 Asbestos Pipe Insulation (Boiler Room)
            {
                "text": "蒸気配管: 石綿保温材 100A",
                "target": (r2["rect"][0] + 120, r2["rect"][1] + 60),
                "elbow": (r2["rect"][0] + 70, r2["rect"][1] + 130),
                "text_pos": (r2["rect"][0] + 20, r2["rect"][1] + 130),
                "angle": 0,
                "asbestos_status": "POSITIVE",
                "hazard_level": "LEVEL_2",
                "matched_material_id": "MAT-L2-001"
            },
            # 3. Level 3 Corrugated Slate (Warehouse Wall) - Rotated 90 degrees
            {
                "text": "外壁: スレート波板 t=6.3",
                "target": (r3["rect"][2] - 15, r3["rect"][1] + 80),
                "elbow": (r3["rect"][2] - 40, r3["rect"][1] + 140),
                "text_pos": (r3["rect"][2] - 50, r3["rect"][1] + 150),
                "angle": 90,
                "asbestos_status": "POSITIVE",
                "hazard_level": "LEVEL_3",
                "matched_material_id": "MAT-L3-001"
            },
            # 4. Safe Non-Asbestos Glasswool (Cavity Wall)
            {
                "text": "間仕切壁: グラスウール保温材 t=50 充填",
                "target": (r4["rect"][0] + 140, r4["rect"][1] + 90),
                "elbow": (r4["rect"][0] + 90, r4["rect"][1] + 160),
                "text_pos": (r4["rect"][0] + 15, r4["rect"][1] + 160),
                "angle": 0,
                "asbestos_status": "NEGATIVE",
                "hazard_level": "NON_ASBESTOS",
                "matched_material_id": "MAT-SAFE-001"
            },
            # 5. Safe Gypsum Board
            {
                "text": "壁: 石膏ボード t=12.5 EP塗装",
                "target": (r5["rect"][0] + 50, r5["rect"][1] + 80),
                "elbow": (r5["rect"][0] + 20, r5["rect"][1] + 140),
                "text_pos": (r5["rect"][0] + 10, r5["rect"][1] + 140),
                "angle": 0,
                "asbestos_status": "NEGATIVE",
                "hazard_level": "NON_ASBESTOS",
                "matched_material_id": "MAT-SAFE-002"
            }
        ]

        for item in callouts:
            tx, ty = item["target"]
            ex, ey = item["elbow"]
            pos_x, pos_y = item["text_pos"]
            text = item["text"]
            angle = item["angle"]

            # Draw pointer arrow / dot and leader line
            draw.ellipse([tx - 4, ty - 4, tx + 4, ty + 4], fill=(0, 0, 0))
            draw.line([tx, ty, ex, ey], fill=(0, 0, 0), width=1)

            font = self.fonts["annotation"]
            bbox = font.getbbox(text)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]

            if angle == 0:
                # Underline leader extension
                draw.line([ex, ey, pos_x + tw, ey], fill=(0, 0, 0), width=1)
                draw.text((pos_x, pos_y - th - 2), text, fill=(0, 0, 0), font=font)
                annotations.append({
                    "text": text,
                    "bbox": [pos_x, pos_y - th - 2, pos_x + tw, pos_y - 2],
                    "polygon": [[pos_x, pos_y - th - 2], [pos_x + tw, pos_y - th - 2], [pos_x + tw, pos_y - 2], [pos_x, pos_y - 2]],
                    "angle": 0,
                    "region_type": "material_callout",
                    "asbestos_status": item["asbestos_status"],
                    "hazard_level": item["hazard_level"],
                    "matched_material_id": item["matched_material_id"]
                })
            elif angle == 90:
                # Render rotated text on temporary canvas
                rot_img = Image.new("RGBA", (tw + 10, th + 10), (255, 255, 255, 0))
                rot_draw = ImageDraw.Draw(rot_img)
                rot_draw.text((5, 5), text, fill=(0, 0, 0), font=font)
                rotated = rot_img.rotate(270, expand=True)  # 90 deg clockwise in image coordinates
                rw, rh = rotated.size
                draw.bitmap((pos_x, pos_y), rotated.convert("L"))
                annotations.append({
                    "text": text,
                    "bbox": [pos_x, pos_y, pos_x + rw, pos_y + rh],
                    "polygon": [[pos_x, pos_y], [pos_x + rw, pos_y], [pos_x + rw, pos_y + rh], [pos_x, pos_y + rh]],
                    "angle": 90,
                    "region_type": "material_callout",
                    "asbestos_status": item["asbestos_status"],
                    "hazard_level": item["hazard_level"],
                    "matched_material_id": item["matched_material_id"]
                })


if __name__ == "__main__":
    generator = CADBlueprintGenerator()
    result = generator.generate("DRAWING-TEST-001", "data/output/clean", seed=42)
    print("Synthetic CAD drawing generated successfully:")
    print(f"Total annotations: {result['annotation_count']}")
    print(f"Asbestos Positive: {result['asbestos_positive_count']}")
    print(f"Non-Asbestos: {result['non_asbestos_count']}")
