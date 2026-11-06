"""
Architectural Drawing Layout & Region Classifier.
Segments and categorizes detected text boxes into:
1. MATERIAL_CALLOUT: Annotations describing materials (candidates for asbestos matching)
2. TABLE_CELL: Cells within Finish Schedules (仕上表)
3. ROOM_LABEL: Room identification headers
4. TITLE_BLOCK: Document metadata (project name, date, scale, drawing number)
5. DIMENSION_NOISE: Numerical measurements, elevation marks (FL, CH, GL), and structural profiles.

Filters out dimension noise to prevent non-material tokens from corrupting the matching engine.
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple, Optional
from enum import Enum
from dataclasses import dataclass


class RegionType(str, Enum):
    MATERIAL_CALLOUT = "MATERIAL_CALLOUT"
    TABLE_CELL = "TABLE_CELL"
    ROOM_LABEL = "ROOM_LABEL"
    TITLE_BLOCK = "TITLE_BLOCK"
    DIMENSION_NOISE = "DIMENSION_NOISE"
    UNCATEGORIZED = "UNCATEGORIZED"


@dataclass
class ClassifiedRegion:
    """Represents a text item with assigned architectural region classification."""
    text: str
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    confidence: float
    region_type: RegionType
    is_asbestos_candidate: bool
    filter_reason: Optional[str] = None


class ArchitecturalRegionClassifier:
    """Classifies detected text regions based on spatial coordinates and domain regex."""

    # Dimension and measurement patterns
    DIMENSION_PATTERNS = [
        re.compile(r"^[\d,\.\s]+$"),                              # Pure numbers like "4,500", "13,500"
        re.compile(r"^\d{2,}$"),                                  # Short digit strings: "00", "150", "4500"
        re.compile(r"^[\.,\-\|\/\\]+$"),                          # Stray punctuation only
        re.compile(r"^\s*$"),                                     # Whitespace / empty
        re.compile(r"^[\d,\.\s\+\-±:/\\①②③④⑤⑥⑦⑧⑨⑩]+$"),          # Numeric/symbols mix
        re.compile(r"^FL\s*[±\+\-]?\d*", re.IGNORECASE),          # Floor level "FL ±0", "FL+150"
        re.compile(r"^\d*SL\s*[±\+\-]?\d*", re.IGNORECASE),       # Slab level "1SL +3,200"
        re.compile(r"^CH\s*=?\s*\d+", re.IGNORECASE),             # Ceiling height "CH=2700" or "CH2700"
        re.compile(r"^GL\s*[±\+\-]?\d*", re.IGNORECASE),          # Ground level "GL ±0"
        re.compile(r"^RFL\s*[±\+\-]?\d*", re.IGNORECASE),         # Roof floor level
        re.compile(r"^[WH]\s*=\s*\d+", re.IGNORECASE),            # Width/Height "W=900 H=2,100"
        re.compile(r"^H-\d+x\d+", re.IGNORECASE),                # Steel H-beam "H-300x150"
        re.compile(r"^\d+\s*x\s*\d+(\s*x\s*\d+)?$"),             # "100 x 50 x 20"
        re.compile(r"^[XYZ]\d+$", re.IGNORECASE),                # Grid bubble "X1", "Y2"
        re.compile(r"^\d+/\d+$"),                                 # Scale or ratio "1/100"
        re.compile(r"^[A-Za-z]{1,3}[\d\s]*$"),                    # Short alpha+digit: "FL", "CH", "A1", "PH2"
        re.compile(r"^[A-Za-z]{1,3}\s*[±\+\-]?\s*\d+$"),          # "EL+150", "GL-50"
        re.compile(r"^[▽△○●□■◎◇◆×]+$"),                           # Survey/marker symbols only
        re.compile(r"^[\-–—]+$"),                                  # Dash / rule lines
        re.compile(r"^[.。・…]+$"),                                 # Dots / ellipses
    ]

    # Minimum requirements for a material callout token
    # Must contain at least one Kanji (CJK Unified) or Katakana character
    _KANJI_RE = re.compile(r"[\u4e00-\u9fff\u30a0-\u30ff]")
    # Tokens shorter than this (after strip) are almost always noise
    MIN_MATERIAL_CHAR_LEN = 3

    # Title block metadata keywords
    TITLE_KEYWORDS = [
        "工事名称", "図面名称", "設計", "作成年月", "図面番号", "縮尺",
        "承認", "担当", "特記事項", "凡例", "株式会社", "設計事務所"
    ]

    # Finish schedule header keywords
    SCHEDULE_HEADERS = [
        "仕上表", "室名", "部屋名", "床", "巾木", "壁", "天井", "下地", "備考",
        "特記仕上表", "FINISH SCHEDULE", "SCHEDULE", "FL", "WALL", "CEILING", "巾木 H=60"
    ]

    # Standard Japanese Room names
    ROOM_NAMES = [
        "機械室", "ボイラー室", "電気室", "事務室", "会議室",
        "給湯室", "便所", "湯沸室", "倉庫", "廊下", "階段室",
        "エントランス", "ホール", "風除室", "配管シャフト", "PS"
    ]

    # Architectural material abbreviations & shorthand (NEVER filter these out)
    ARCHITECTURAL_SHORTHAND = {
        "PB", "ALC", "EP", "VP", "RC", "PC", "OP", "DP", "A種", "B種",
        "F板", "石綿", "合板", "波板", "直押", "金ゴテ", "なし", "同上",
        "けい酸", "ケイカル", "フレキ", "コロニアル", "カラーベスト", "モルタル", "プラスター"
    }

    def __init__(self, sheet_width: int = 2400, sheet_height: int = 1600):
        self.sheet_width = sheet_width
        self.sheet_height = sheet_height

    def classify(
        self,
        text: str,
        bbox: List[float],
        confidence: float = 1.0,
        table_bbox: Optional[List[float]] = None
    ) -> ClassifiedRegion:
        """
        Categorizes a text bounding box and determines if it is an asbestos candidate.
        Ensures valid architectural materials and table cells are NEVER mistakenly dropped.
        """
        cleaned = text.strip()

        # 0. Empty / whitespace-only is always discarded
        if not cleaned:
            return ClassifiedRegion(
                text=cleaned, bbox=bbox, confidence=confidence,
                region_type=RegionType.DIMENSION_NOISE, is_asbestos_candidate=False,
                filter_reason="Empty token"
            )

        # 1. PRIORITY: Finish Schedule Table Cells
        # If inside table boundary, preserve ALL finish cells!
        x_min, y_min, x_max, y_max = bbox
        if table_bbox is not None:
            tx1, ty1, tx2, ty2 = table_bbox
            if x_min >= tx1 - 15 and x_max <= tx2 + 15 and y_min >= ty1 - 15 and y_max <= ty2 + 15:
                is_header = any(h == cleaned or h in cleaned for h in self.SCHEDULE_HEADERS)
                if is_header and not any(m in cleaned for m in ["t=", "mm", "吹付", "波板", "タイル", "ボード", "ウール", "保温"]):
                    return ClassifiedRegion(
                        text=cleaned, bbox=bbox, confidence=confidence,
                        region_type=RegionType.TABLE_CELL, is_asbestos_candidate=False,
                        filter_reason="Table column header label"
                    )
                # Any non-header cell inside the Finish Schedule is a valid material finish candidate!
                return ClassifiedRegion(
                    text=cleaned, bbox=bbox, confidence=confidence,
                    region_type=RegionType.TABLE_CELL, is_asbestos_candidate=True
                )

        # 2. PRIORITY: Whitelisted Architectural Shorthand & Abbreviations
        if cleaned.upper() in self.ARCHITECTURAL_SHORTHAND or any(sh == cleaned for sh in self.ARCHITECTURAL_SHORTHAND):
            return ClassifiedRegion(
                text=cleaned, bbox=bbox, confidence=confidence,
                region_type=RegionType.MATERIAL_CALLOUT, is_asbestos_candidate=True
            )

        # 3. Check for Title Block Region (usually bottom right corner or metadata strip)
        is_bottom_right = (x_min > self.sheet_width * 0.65 and y_min > self.sheet_height * 0.75)
        has_title_kw = any(kw in cleaned for kw in self.TITLE_KEYWORDS)
        if has_title_kw or (is_bottom_right and any(w in cleaned for w in ["設計", "図面", "昭和", "198", "縮尺"])):
            return ClassifiedRegion(
                text=cleaned, bbox=bbox, confidence=confidence,
                region_type=RegionType.TITLE_BLOCK, is_asbestos_candidate=False,
                filter_reason="Identified as Title Block drawing metadata"
            )

        # 4. Check for Room Label
        if any(r == cleaned or cleaned.startswith(r) for r in self.ROOM_NAMES) and not any(m in cleaned for m in ["t=", "mm", "吹付", "波板", "タイル"]):
            return ClassifiedRegion(
                text=cleaned, bbox=bbox, confidence=confidence,
                region_type=RegionType.ROOM_LABEL, is_asbestos_candidate=False,
                filter_reason="Identified as Room Header"
            )

        # 5. Dimension & Measurement Noise Filter
        # Only discard tokens that strictly match numerical dimensions or elevation marks
        for pat in self.DIMENSION_PATTERNS:
            if pat.search(cleaned):
                return ClassifiedRegion(
                    text=cleaned, bbox=bbox, confidence=confidence,
                    region_type=RegionType.DIMENSION_NOISE, is_asbestos_candidate=False,
                    filter_reason="Matched numerical dimension or elevation pattern"
                )

        # 6. Default: Valid Material Callout Annotation (preserved for matching)
        return ClassifiedRegion(
            text=cleaned, bbox=bbox, confidence=confidence,
            region_type=RegionType.MATERIAL_CALLOUT, is_asbestos_candidate=True
        )

    def filter_candidates(self, regions: List[ClassifiedRegion]) -> List[ClassifiedRegion]:
        """Returns only candidate regions that should be evaluated by the matching engine."""
        return [r for r in regions if r.is_asbestos_candidate]

