"""
Unit and Integration Tests for Tier-5 Local LLM Arbitrator (Qwen3:1.7B).
Tests:
1. Health check & model detection (both online & offline modes)
2. Robust JSON parsing and fallback validation
3. Offline graceful fallback (leaves diagnoses intact without exceptions)
4. Live end-to-end arbitration with local Ollama qwen3:1.7b (if running)
"""

import tempfile
from pathlib import Path
from nlp.llm_arbitrator import LocalLLMArbitrator
from nlp.classifier import AsbestosDiagnosticClassifier, DrawingItemDiagnosis
from nlp.matcher import MatchTier
from data.database.db_manager import AsbestosStatus, HazardLevel, MaterialsDatabase
from data.database.learned_cache import LearnedMaterialCache
from nlp.matcher import AsbestosMatchingEngine


def test_llm_json_parser_robustness():
    arbitrator = LocalLLMArbitrator()

    # Case 1: Standard clean JSON response
    valid_json = """
    {
      "results": [
        {
          "id": "ITEM-001",
          "status": "POSITIVE",
          "hazard_level": "LEVEL_3",
          "matched_material_ja": "けい酸カルシウム板第1種",
          "matched_material_en": "Asbestos Calcium Silicate Board Type 1",
          "confidence": 0.95,
          "reasoning": "石綿ケイカル is common Japanese shorthand for Level 3 Calcium Silicate Board Type 1."
        },
        {
          "id": "ITEM-002",
          "status": "NEGATIVE",
          "hazard_level": "NON_ASBESTOS",
          "matched_material_ja": "グラスウール保温材",
          "matched_material_en": "Glass Wool Thermal Insulation",
          "confidence": 0.98,
          "reasoning": "GW保温材 stands for Glass Wool, which contains no asbestos."
        }
      ]
    }
    """
    parsed = arbitrator._parse_llm_json(valid_json)
    assert len(parsed) == 2
    assert parsed["ITEM-001"]["status"] == "POSITIVE"
    assert parsed["ITEM-001"]["hazard_level"] == "LEVEL_3"
    assert parsed["ITEM-001"]["confidence"] == 0.95
    assert parsed["ITEM-002"]["status"] == "NEGATIVE"
    assert parsed["ITEM-002"]["hazard_level"] == "NON_ASBESTOS"

    # Case 2: Markdown fenced JSON
    markdown_json = f"Here is your classification:\n```json\n{valid_json}\n```\nHope this helps!"
    parsed_md = arbitrator._parse_llm_json(markdown_json)
    assert len(parsed_md) == 2
    assert "ITEM-001" in parsed_md

    # Case 3: Malformed / invalid response gracefully returns empty dict
    assert arbitrator._parse_llm_json("This is not valid json") == {}


def test_llm_offline_graceful_fallback():
    # Configure an unreachable port to simulate offline Ollama
    offline_arbitrator = LocalLLMArbitrator(ollama_url="http://localhost:59999", enabled=True)
    assert offline_arbitrator.is_available() is False

    classifier = AsbestosDiagnosticClassifier(llm_arbitrator=offline_arbitrator)

    # Item with unknown material that produces UNCERTAIN in tiers 1-4
    raw_items = [
        {"text": "未確認謎の輸入複合パネル t=30", "bbox": [100, 100, 200, 120]}
    ]

    diagnoses = classifier.diagnose_drawing(raw_items)
    assert len(diagnoses) == 1
    # Offline mode must leave item as UNCERTAIN without crashing or throwing
    assert diagnoses[0].status == "UNCERTAIN"
    assert diagnoses[0].requires_human_review is True


def test_live_llm_arbitration_if_available():
    live_arbitrator = LocalLLMArbitrator(model_name="qwen3:1.7b")

    if not live_arbitrator.is_available():
        print("Local Ollama or qwen3:1.7b not currently available, skipping live test.")
        return

    print("Ollama qwen3:1.7b detected. Running live arbitration test...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_cache = LearnedMaterialCache(cache_file=Path(tmp_dir) / "test_live_cache.json")
        isolated_arbitrator = LocalLLMArbitrator(model_name="qwen3:1.7b", learned_cache=temp_cache)
        isolated_db = MaterialsDatabase(learned_cache=temp_cache)
        classifier = AsbestosDiagnosticClassifier(
            db=isolated_db,
            llm_arbitrator=isolated_arbitrator
        )

        # Shorthand, colloquial, everyday room names, and ambiguous brand items
        test_items = [
            {"text": "石綿ケイカル t=6", "bbox": [100, 100, 250, 130], "room": "湯沸室"},
            {"text": "GW保温材 50A", "bbox": [300, 100, 450, 130], "room": "PSシャフト"},
            {"text": "機械室", "bbox": [500, 100, 600, 130], "room": "B1F"},
            {"text": "耐水", "bbox": [700, 100, 780, 130], "room": "浴室"},
            {"text": "謎の商標パネル ハイベストX", "bbox": [800, 100, 950, 130], "room": "倉庫"}
        ]

        diagnoses = classifier.diagnose_drawing(test_items, table_bbox=[0, 0, 2000, 2000])
        assert len(diagnoses) == 5

        diag_dict = {d.raw_text: d for d in diagnoses}

        # Verify that the LLM arbitrated the items
        for text, diag in diag_dict.items():
            flag = "REVIEW_REQUIRED ⚠️" if diag.requires_human_review else "OK ✅"
            print(f"Item: '{text}' -> {diag.status} [{diag.hazard_level}] (Tier: {diag.match_tier}) [{flag}]")
            print(f"  Reasoning: {diag.regulatory_citation}")

        # Check that asbestos material is classified as POSITIVE or UNCERTAIN requiring safety review
        assert diag_dict["石綿ケイカル t=6"].status in ("POSITIVE", "UNCERTAIN")

        # Check that everyday room names and specs are NEGATIVE (NON_ASBESTOS) and do NOT require human review
        assert diag_dict["機械室"].status == "NEGATIVE"
        assert diag_dict["機械室"].hazard_level == "NON_ASBESTOS"
        assert diag_dict["機械室"].requires_human_review is False

        assert diag_dict["耐水"].status == "NEGATIVE"
        assert diag_dict["耐水"].hazard_level == "NON_ASBESTOS"
        assert diag_dict["耐水"].requires_human_review is False

        # Check that ambiguous trade name was arbitrated by Tier-5 LLM
        assert diag_dict["謎の商標パネル ハイベストX"].match_tier == MatchTier.TIER_5_LLM.value
        assert diag_dict["謎の商標パネル ハイベストX"].status in ("UNCERTAIN", "POSITIVE", "NEGATIVE")


def test_unidentified_material_map_deduplication_and_broadcast():
    """Verifies that identical material candidates across multiple pages and coordinates are deduplicated and correctly broadcast."""
    from nlp.llm_arbitrator import UnidentifiedMaterialMap

    material_map = UnidentifiedMaterialMap()

    # Three occurrences of the same material across pages 1, 2, and 3 with distinct bboxes and rooms
    occ1 = DrawingItemDiagnosis(
        item_id="ITEM-001",
        raw_text="GW保温材 50A",
        normalized_text="GW保温材 50A",
        bbox=[100, 100, 200, 150],
        region_type="DETAIL_CALLOUT",
        room_context="PSシャフト",
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
    occ2 = DrawingItemDiagnosis(
        item_id="ITEM-002",
        raw_text="GW保温材 50A",
        normalized_text="GW保温材 50A",
        bbox=[300, 300, 400, 350],
        region_type="DETAIL_CALLOUT",
        room_context="機械室",
        status="UNCERTAIN",
        hazard_level="UNCERTAIN",
        matched_material_ja="該当なし (None)",
        matched_material_en="None",
        confidence=0.0,
        match_tier="NO_MATCH",
        requires_human_review=True,
        regulatory_citation="",
        page_number=2
    )
    occ3 = DrawingItemDiagnosis(
        item_id="ITEM-003",
        raw_text="GW保温材 50A",
        normalized_text="GW保温材 50A",
        bbox=[500, 500, 600, 550],
        region_type="DETAIL_CALLOUT",
        room_context="ボイラー室",
        status="UNCERTAIN",
        hazard_level="UNCERTAIN",
        matched_material_ja="該当なし (None)",
        matched_material_en="None",
        confidence=0.0,
        match_tier="NO_MATCH",
        requires_human_review=True,
        regulatory_citation="",
        page_number=3
    )
    occ4 = DrawingItemDiagnosis(
        item_id="ITEM-004",
        raw_text="未特定防火パネル",
        normalized_text="未特定防火パネル",
        bbox=[50, 50, 120, 80],
        region_type="WALL_FINISH",
        room_context="倉庫",
        status="UNCERTAIN",
        hazard_level="UNCERTAIN",
        matched_material_ja="該当なし (None)",
        matched_material_en="None",
        confidence=0.0,
        match_tier="NO_MATCH",
        requires_human_review=True,
        regulatory_citation="",
        page_number=2
    )

    for d in [occ1, occ2, occ3, occ4]:
        material_map.add(d)

    # 4 total occurrences must be deduplicated to 2 unique material candidates
    assert material_map.total_occurrences == 4
    assert material_map.total_unique == 2

    payload = material_map.get_unique_payload()
    assert len(payload) == 2

    gw_payload = [p for p in payload if "GW保温材" in p["raw_text"]][0]
    # Check that room context from all pages was aggregated
    assert "PSシャフト" in gw_payload["room_context"]
    assert "機械室" in gw_payload["room_context"]
    assert "ボイラー室" in gw_payload["room_context"]

    # Simulate LLM response for the single unique GW material
    mock_llm_results = {
        gw_payload["item_id"]: {
            "id": gw_payload["item_id"],
            "status": "NEGATIVE",
            "hazard_level": "NON_ASBESTOS",
            "matched_material_ja": "グラスウール保温材",
            "matched_material_en": "Glass Wool Thermal Insulation",
            "confidence": 0.98,
            "reasoning": "GW is non-asbestos glass wool."
        }
    }

    updated_count = material_map.broadcast_results(mock_llm_results, model_name="qwen3:1.7b")
    # All 3 occurrences across pages 1, 2, and 3 must be updated
    assert updated_count == 3

    # Verify that spatial coordinates & page numbers are strictly preserved!
    assert occ1.bbox == [100, 100, 200, 150]
    assert occ1.page_number == 1
    assert occ1.item_id == "ITEM-001"
    assert occ1.status == "NEGATIVE"
    assert occ1.hazard_level == "NON_ASBESTOS"
    assert occ1.requires_human_review is False

    assert occ2.bbox == [300, 300, 400, 350]
    assert occ2.page_number == 2
    assert occ2.item_id == "ITEM-002"
    assert occ2.status == "NEGATIVE"

    assert occ3.bbox == [500, 500, 600, 550]
    assert occ3.page_number == 3
    assert occ3.item_id == "ITEM-003"
    assert occ3.status == "NEGATIVE"

    # Non-updated item remains UNCERTAIN
    assert occ4.status == "UNCERTAIN"


def test_multipage_deferred_arbitration_flow():
    """Verifies that multi-page scanning defers Tier-5 LLM and then arbitrates once at the end."""
    classifier = AsbestosDiagnosticClassifier()

    page1_items = [
        {"text": "未確認輸入パネル X-100", "bbox": [10, 10, 50, 30], "page_num": 1},
        {"text": "石綿ケイカル t=6", "bbox": [100, 100, 200, 130], "page_num": 1}
    ]
    page2_items = [
        {"text": "未確認輸入パネル X-100", "bbox": [300, 300, 350, 320], "page_num": 2},
        {"text": "プラスターボード t=9.5", "bbox": [400, 400, 500, 430], "page_num": 2}
    ]

    # Pass 1: Scan page 1 and page 2 with LLM disabled
    p1_diag = classifier.diagnose_drawing(page1_items, page_number=1, enable_llm=False)
    p2_diag = classifier.diagnose_drawing(page2_items, page_number=2, enable_llm=False)

    all_diag = p1_diag + p2_diag
    assert len(all_diag) == 4

    # Before LLM arbitration, unknown panel items are UNCERTAIN (Tiers 1-4 no match)
    unknown_items = [d for d in all_diag if "未確認輸入パネル" in d.raw_text]
    assert len(unknown_items) == 2
    for item in unknown_items:
        assert item.status == "UNCERTAIN"

    # Pass 2 & 3: Run end-of-document arbitration
    if classifier.llm_arbitrator and classifier.llm_arbitrator.is_available():
        all_diag = classifier.arbitrate_diagnoses(all_diag)
        # Verify deduplicated map was built
        assert classifier.llm_arbitrator.last_material_map is not None
        # Both unknown items across page 1 and page 2 should now be arbitrated
        for item in unknown_items:
            assert item.status in ("POSITIVE", "NEGATIVE", "UNCERTAIN")
            assert item.match_tier == MatchTier.TIER_5_LLM.value


if __name__ == "__main__":
    print("Testing JSON parser robustness...")
    test_llm_json_parser_robustness()
    print("Testing offline graceful fallback...")
    test_llm_offline_graceful_fallback()
    print("Testing live arbitration (if available)...")
    test_live_llm_arbitration_if_available()
    print("All Tier-5 LLM Arbitrator tests passed successfully!")
