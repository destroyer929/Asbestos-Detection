"""
Unit & Integration Tests for Jamdict Semantic Filter & Persistent Learned Material Cache.
Verifies:
1. Jamdict offline linguistic filtering of rooms, construction actions, and structural noise.
2. Protection of genuine building materials and unlisted Katakana trade names.
3. Gate 4 auto-resolution of non-materials with Zero Ollama calls.
4. Persistent Learned Material Cache:
   - Strictly caches POSITIVE and NEGATIVE classifications.
   - Strictly EXCLUDES UNCERTAIN classifications.
   - Injects learned materials into Tier 1 exact index for < 1ms resolution on future scans.
"""

import tempfile
from pathlib import Path
from nlp.jamdict_filter import get_jamdict_filter
from nlp.llm_arbitrator import check_material_candidate, is_valid_material_candidate, LocalLLMArbitrator
from data.database.learned_cache import LearnedMaterialCache, LearnedRecord
from data.database.db_manager import MaterialsDatabase
from nlp.matcher import AsbestosMatchingEngine, MatchTier
from nlp.classifier import AsbestosDiagnosticClassifier, DrawingItemDiagnosis


def test_jamdict_linguistic_filter_categories():
    """Verifies that Jamdict correctly segments rooms, actions, and protects real materials."""
    jf = get_jamdict_filter()

    # Rooms / spaces must be identified as non-material
    for room in ["便所", "機械室", "更衣室", "倉庫", "車庫", "浴室", "階段室"]:
        is_non_mat, reason = jf.is_non_material(room)
        assert is_non_mat is True, f"Expected {room} to be identified as non-material room"
        assert "room" in reason.lower() or "space" in reason.lower() or "toilet" in reason.lower()

    # Construction actions and drawing notes must be identified as non-material
    for action in ["撤去", "補修", "工事", "特記"]:
        is_non_mat, reason = jf.is_non_material(action)
        assert is_non_mat is True, f"Expected {action} to be identified as non-material action"
        assert "action" in reason.lower() or "note" in reason.lower() or "construction" in reason.lower() or "repair" in reason.lower()

    # Non-material structural elements
    for struct in ["下地", "目地"]:
        is_non_mat, reason = jf.is_non_material(struct)
        assert is_non_mat is True, f"Expected {struct} to be identified as structural non-material"

    # Genuine building materials MUST be protected (is_non_material == False)
    for mat in ["スレート", "ロックウール", "モルタル", "石綿", "アスベスト"]:
        is_non_mat, reason = jf.is_non_material(mat)
        assert is_non_mat is False, f"Expected {mat} to be protected as a building material"

    # Unlisted brand names (0 entries) MUST NOT be filtered out by Jamdict
    for trade in ["ブロベスト", "スターベスト", "ダイロートン"]:
        is_non_mat, reason = jf.is_non_material(trade)
        assert is_non_mat is False, f"Expected trade name {trade} to be preserved for Tier 5"


def test_gate4_material_candidate_checking():
    """Verifies Gate 4 candidate evaluation and rejection rationale."""
    # Room names should fail Gate 4
    assert is_valid_material_candidate("便所") is False
    assert is_valid_material_candidate("機械室") is False

    # Action notes should fail Gate 4
    assert is_valid_material_candidate("既存撤去") is False or is_valid_material_candidate("撤去") is False
    assert is_valid_material_candidate("補修") is False
    assert is_valid_material_candidate("工事") is False

    # Genuine materials and trade names must pass Gate 4
    assert is_valid_material_candidate("ブロベスト") is True
    assert is_valid_material_candidate("スターベスト") is True
    assert is_valid_material_candidate("ハイモルタル") is True
    assert is_valid_material_candidate("ケイカル板 t=6") is True


def test_gate4_returns_gate4_tier():
    """Verifies that non-materials filtered at Gate 4 return MatchTier.GATE_4 and NEVER TIER_5_LLM."""
    arbitrator = LocalLLMArbitrator(enabled=True)
    item = DrawingItemDiagnosis(
        item_id="ITEM-TEST-G4",
        raw_text="機械室",
        normalized_text="機械室",
        bbox=[100, 100, 200, 150],
        region_type="GENERAL_NOTES",
        room_context="",
        status="UNCERTAIN",
        hazard_level="UNCERTAIN",
        matched_material_ja="該当なし (None)",
        matched_material_en="None",
        confidence=0.0,
        match_tier="NO_MATCH",
        requires_human_review=True,
        regulatory_citation="",
        page_number=1
    )

    arbitrated = arbitrator.arbitrate_diagnoses([item])
    assert len(arbitrated) == 1
    diag = arbitrated[0]
    assert diag.status == "NEGATIVE"
    assert diag.hazard_level == "NON_ASBESTOS"
    assert diag.match_tier == MatchTier.GATE_4.value
    assert diag.match_tier != MatchTier.TIER_5_LLM.value
    assert "Gate 4 Auto-Resolved" in diag.regulatory_citation


def test_persistent_learned_cache_strict_rules():
    """Verifies that LearnedMaterialCache saves only POSITIVE and NEGATIVE and rejects UNCERTAIN."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_path = Path(tmp_dir) / "test_learned.json"
        cache = LearnedMaterialCache(cache_file=cache_path)

        # 1. POSITIVE should be saved
        res_pos = cache.record_decision(
            query_text="テスト石綿スレート",
            status="POSITIVE",
            hazard_level="LEVEL_3",
            matched_material_ja="テスト石綿スレート波板",
            matched_material_en="Test Asbestos Slate",
            confidence=0.92,
            reasoning="Valid asbestos product"
        )
        assert res_pos is True
        assert len(cache) == 1

        # 2. NEGATIVE should be saved
        res_neg = cache.record_decision(
            query_text="テスト無石綿ボード",
            status="NEGATIVE",
            hazard_level="NON_ASBESTOS",
            matched_material_ja="無石綿ボード",
            matched_material_en="Non-Asbestos Board",
            confidence=0.95,
            reasoning="Verified non-asbestos"
        )
        assert res_neg is True
        assert len(cache) == 2

        # 3. UNCERTAIN must STRICTLY be rejected
        res_unc = cache.record_decision(
            query_text="謎の不明建材",
            status="UNCERTAIN",
            hazard_level="UNCERTAIN",
            matched_material_ja="未特定",
            matched_material_en="Uncertain",
            confidence=0.50,
            reasoning="Cannot determine"
        )
        assert res_unc is False, "LearnedMaterialCache must NEVER save UNCERTAIN items!"
        assert len(cache) == 2  # Count unchanged

        # 4. Low confidence (< 0.75) must be rejected
        res_low_conf = cache.record_decision(
            query_text="低信頼度ボード",
            status="POSITIVE",
            hazard_level="LEVEL_3",
            matched_material_ja="低信頼度ボード",
            matched_material_en="Low Conf",
            confidence=0.60,
            reasoning="Weak match"
        )
        assert res_low_conf is False
        assert len(cache) == 2

        # 5. Reload cache from disk to verify persistence
        new_cache = LearnedMaterialCache(cache_file=cache_path)
        assert len(new_cache) == 2
        rec = new_cache.lookup("テスト石綿スレート")
        assert rec is not None
        assert rec.status == "POSITIVE"
        assert rec.hazard_level == "LEVEL_3"


def test_learned_cache_tier1_fast_match():
    """Verifies that items in the learned cache resolve instantly in Tier 1 with 0 LLM calls."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_path = Path(tmp_dir) / "test_learned.json"
        cache = LearnedMaterialCache(cache_file=cache_path)

        # Pre-seed cache with a learned trade material
        cache.record_decision(
            query_text="エースライト",
            status="POSITIVE",
            hazard_level="LEVEL_2",
            matched_material_ja="けい酸カルシウム保温材第1種 (エースライト)",
            matched_material_en="Calcium Silicate Insulation Type 1 (Acelite)",
            confidence=0.96,
            reasoning="Acelite is a historical trade name for Level 2 calcium silicate pipe insulation."
        )

        # Initialize database with this learned cache
        db = MaterialsDatabase(learned_cache=cache)
        matcher = AsbestosMatchingEngine(db=db)

        # Query the exact learned material
        result = matcher.match("エースライト")

        # Must resolve at Tier 1 Exact Match!
        assert result.match_tier == MatchTier.TIER_1_EXACT
        assert result.status == "POSITIVE"
        assert result.hazard_level == "LEVEL_2"
        assert result.similarity_score == 1.0
        assert "Tier 1 Learned Cache" in result.explanation
