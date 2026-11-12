"""
Risk-Aware Asbestos Diagnostics & Classification Engine.
Combines:
1. Spatial region context (Finish Schedule cells, Room headers, Callout annotations)
2. Normalization and Japanese tokenization
3. 4-Tier Hierarchical Matching against Japanese MLIT standards
4. Safety-first Human-in-the-Loop triage (routing UNCERTAIN / low-confidence items)
"""

from __future__ import annotations
import uuid
import re
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict

from data.database.db_manager import MaterialsDatabase, HazardLevel, AsbestosStatus
from nlp.normalizer import TextNormalizer, NormalizedText
from nlp.tokenizer import JapaneseMorphologicalTokenizer
from nlp.matcher import AsbestosMatchingEngine, MatchResult, MatchTier
from models.layout.region_classifier import ArchitecturalRegionClassifier, ClassifiedRegion, RegionType
from nlp.llm_arbitrator import LocalLLMArbitrator


@dataclass
class DrawingItemDiagnosis:
    """Final diagnostic determination for a detected building drawing item."""
    item_id: str
    raw_text: str
    normalized_text: str
    bbox: List[float]  # [x_min, y_min, x_max, y_max]
    region_type: str
    room_context: str
    status: AsbestosStatus  # POSITIVE, NEGATIVE, UNCERTAIN
    hazard_level: HazardLevel  # LEVEL_1, LEVEL_2, LEVEL_3, NON_ASBESTOS, UNCERTAIN
    matched_material_ja: str
    matched_material_en: str
    confidence: float
    match_tier: str
    requires_human_review: bool
    regulatory_citation: str
    page_number: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AsbestosDiagnosticClassifier:
    """End-to-end classifier transforming detected text boxes into safety diagnoses."""

    def __init__(
        self,
        db: Optional[MaterialsDatabase] = None,
        llm_arbitrator: Optional[LocalLLMArbitrator] = None,
        enable_llm: bool = True
    ):
        self.db = db or MaterialsDatabase()
        self.normalizer = TextNormalizer()
        self.tokenizer = JapaneseMorphologicalTokenizer(split_mode="B")
        self.matcher = AsbestosMatchingEngine(db=self.db)
        self.region_classifier = ArchitecturalRegionClassifier()
        self.enable_llm = enable_llm
        self.llm_arbitrator = llm_arbitrator or LocalLLMArbitrator(enabled=enable_llm)

    def diagnose_item(
        self,
        raw_text: str,
        bbox: List[float],
        ocr_confidence: float = 1.0,
        room_context: str = "",
        table_bbox: Optional[List[float]] = None,
        page_number: int = 1
    ) -> Optional[DrawingItemDiagnosis]:
        """
        Diagnoses a single detected text box:
        1. Classifies region (filters out dimensions / elevation noise)
        2. Normalizes text
        3. Front-Door Gatekeeper: SudachiPy POS check + Architectural Whitelist
        4. Matches against MLIT database
        5. Calculates safety-critical risk level
        Returns None if item is non-material noise (e.g. dimension numbers).
        """
        # 1. Classify Region
        region_res: ClassifiedRegion = self.region_classifier.classify(
            raw_text, bbox, confidence=ocr_confidence, table_bbox=table_bbox
        )

        # If it is numerical dimension noise, title block, or room title, do not match as material
        if not region_res.is_asbestos_candidate:
            return None

        # 2. Normalize Text
        norm_res: NormalizedText = self.normalizer.normalize(raw_text)
        cleaned_norm = norm_res.cleaned_text.strip()

        # Discard if normalization results in empty string
        if not cleaned_norm:
            return None

        # -------------------------------------------------------------
        # FRONT-DOOR LINGUISTIC & ARCHITECTURAL GATEKEEPER (BEFORE TIER 1)
        # -------------------------------------------------------------
        # GATE 2: Architectural Whitelist Gate
        is_shorthand = (
            cleaned_norm.upper() in self.region_classifier.ARCHITECTURAL_SHORTHAND
            or any(sh == cleaned_norm for sh in self.region_classifier.ARCHITECTURAL_SHORTHAND)
        )

        if not is_shorthand:
            # Strip surrounding punctuation and brackets for pure text evaluation
            cleaned_pure = re.sub(r"^[\s:;,\-\.\'\"（(【\[\)=~`\*\[\]{}<>]+", "", cleaned_norm)
            cleaned_pure = re.sub(r"[\s:;,\-\.\'\"）)】\]\)=~`\*\[\]{}<>]+$", "", cleaned_pure).strip()
            if not cleaned_pure:
                return None

            # Discard non-Japanese alphanumeric, dimension, formula, or symbol strings
            # (e.g. '1* 790', 'X1a', '2.70g', '0L9', 'StQUL', 'L-1+L-4', 'W00,D150.H1', '(4)')
            if re.match(r"^[\d\s.,\*\+~=\-°/%×€$¥#@&_:\(\)\[\]\{\}<>\'\"\\a-zA-Z]+$", cleaned_norm):
                return None

            # Must contain Japanese script (Kanji, Katakana, Hiragana)
            japanese_chars = re.findall(r"[\u4e00-\u9fff\u30a0-\u30ff\u3040-\u309f]", cleaned_pure)
            if not japanese_chars:
                return None

            # Discard isolated 1-character fragments (e.g. '什', '百', '是', '品', '国', '中', '日', '土', '号', '工')
            if len(japanese_chars) <= 1 and "".join(japanese_chars) != "石綿":
                return None

            # GATE 3: SudachiPy Morphological POS Gate
            tokens = self.tokenizer.tokenize(cleaned_pure)
            content_morphemes = [
                t for t in tokens
                if t.is_content_word
                and t.part_of_speech[0] in ("名詞", "動詞", "形容詞")
                and (len(t.part_of_speech) < 2 or t.part_of_speech[1] not in ("数詞", "非自立", "接尾", "助数詞"))
                and len(t.surface.strip()) > 0
            ]
            if not content_morphemes:
                # Text consists solely of numerals, auxiliary particles, or symbols
                return None

        # 3. Match against Asbestos Database
        match_res: MatchResult = self.matcher.match(cleaned_norm)

        # 4. Determine if human review is needed (Safety triage)
        # Any UNCERTAIN item or any match with confidence < 0.82 requires human sign-off
        requires_review = (
            match_res.is_uncertain
            or match_res.similarity_score < 0.82
            or (match_res.hazard_level == "LEVEL_1" and match_res.match_tier == MatchTier.TIER_3_FUZZY)
        )

        item_id = f"ITEM-{uuid.uuid4().hex[:8].upper()}"

        matched_ja = match_res.matched_entry.canonical_name_ja if match_res.matched_entry else "該当なし (None)"
        matched_en = match_res.matched_entry.canonical_name_en if match_res.matched_entry else "None"
        citation = match_res.matched_entry.regulatory_note if match_res.matched_entry else match_res.explanation

        return DrawingItemDiagnosis(
            item_id=item_id,
            raw_text=raw_text,
            normalized_text=norm_res.cleaned_text,
            bbox=bbox,
            region_type=region_res.region_type.value,
            room_context=room_context,
            status=match_res.status,
            hazard_level=match_res.hazard_level,
            matched_material_ja=matched_ja,
            matched_material_en=matched_en,
            confidence=float(match_res.similarity_score),
            match_tier=match_res.match_tier.value,
            requires_human_review=requires_review,
            regulatory_citation=citation,
            page_number=page_number
        )

    def diagnose_drawing(
        self,
        detected_items: List[Dict[str, Any]],
        table_bbox: Optional[List[float]] = None,
        page_number: int = 1,
        enable_llm: Optional[bool] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> List[DrawingItemDiagnosis]:
        """Processes an entire sheet of detected text boxes into structured diagnoses."""
        diagnoses: List[DrawingItemDiagnosis] = []

        for item in detected_items:
            raw_text = item.get("text", "")
            bbox = item.get("bbox", [0, 0, 0, 0])
            conf = item.get("confidence", 1.0)
            room = item.get("room", "")

            diag = self.diagnose_item(
                raw_text=raw_text,
                bbox=bbox,
                ocr_confidence=conf,
                room_context=room,
                table_bbox=table_bbox,
                page_number=item.get("page_num", page_number)
            )
            if diag is not None:
                diagnoses.append(diag)

        # Tier-5: Local LLM Arbitration for UNCERTAIN items
        run_llm = self.enable_llm if enable_llm is None else enable_llm
        if run_llm and self.llm_arbitrator:
            diagnoses = self.llm_arbitrator.arbitrate_diagnoses(
                diagnoses,
                progress_callback=progress_callback
            )

        return diagnoses


if __name__ == "__main__":
    classifier = AsbestosDiagnosticClassifier()

    sample_sheet_items = [
        {"text": "4,500", "bbox": [100, 50, 180, 70]},                              # Dimension -> Ignored
        {"text": "FL ±0", "bbox": [300, 300, 360, 320]},                             # Elevation -> Ignored
        {"text": "機械室", "bbox": [200, 200, 280, 230]},                            # Room label -> Ignored
        {"text": "鉄骨梁: 吹付けロックウール t=25", "bbox": [150, 180, 450, 210]},     # Level 1 Spray
        {"text": "蒸気配管: 石綿保温材 100A", "bbox": [500, 200, 750, 230]},          # Level 2 Pipe Cover
        {"text": "スレート波板 t=6.3", "bbox": [1400, 350, 1600, 380]},               # Level 3 Slate
        {"text": "プラスターボード t=9.5", "bbox": [800, 600, 1050, 630]},           # Safe Drywall
        {"text": "吹付ロクウール", "bbox": [200, 400, 350, 430]}                      # Fuzzy Typo -> Review Flagged
    ]

    print("Diagnosing Sample Drawing Sheet Annotations:\n")
    results = classifier.diagnose_drawing(sample_sheet_items)
    print(f"Total input text items: {len(sample_sheet_items)}")
    print(f"Material candidates identified: {len(results)} (Dimensions/Noise filtered out)\n")

    for d in results:
        flag = "⚠️ REVIEW REQUIRED" if d.requires_human_review else "✅ CONFIDENT"
        badge = "🔴" if d.status == "POSITIVE" else "🟢"
        print(f"[{d.item_id}] {badge} {d.status} ({d.hazard_level}) - {flag}")
        print(f"  Raw Text : '{d.raw_text}' -> Normalized: '{d.normalized_text}'")
        print(f"  Matched  : {d.matched_material_ja} ({d.matched_material_en})")
        print(f"  Tier     : {d.match_tier} (Score: {d.confidence:.2f})")
        print(f"  Citation : {d.regulatory_citation}\n")

