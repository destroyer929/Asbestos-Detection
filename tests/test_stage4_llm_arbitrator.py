"""
Unit and Integration Tests for Tier-5 Local LLM Arbitrator (Qwen2.5-VL-3B).
Tests:
1. Health check & model detection (both online & offline modes)
2. Robust JSON parsing and fallback validation
3. Offline graceful fallback (leaves diagnoses intact without exceptions)
4. Live end-to-end arbitration with local Ollama qwen2.5vl:3b (if running)
"""

from nlp.llm_arbitrator import LocalLLMArbitrator
from nlp.classifier import AsbestosDiagnosticClassifier, DrawingItemDiagnosis
from nlp.matcher import MatchTier
from data.database.db_manager import AsbestosStatus, HazardLevel


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
    live_arbitrator = LocalLLMArbitrator(model_name="qwen2.5vl:3b")

    if not live_arbitrator.is_available():
        print("Local Ollama or qwen2.5vl:3b not currently available, skipping live test.")
        return

    print("Ollama qwen2.5vl:3b detected. Running live arbitration test...")
    classifier = AsbestosDiagnosticClassifier(llm_arbitrator=live_arbitrator)

    # Shorthand or colloquial items that might be UNCERTAIN in classical regex/fuzzy matching
    test_items = [
        {"text": "石綿ケイカル t=6", "bbox": [100, 100, 250, 130], "room": "湯沸室"},
        {"text": "GW保温材 50A", "bbox": [300, 100, 450, 130], "room": "PSシャフト"}
    ]

    diagnoses = classifier.diagnose_drawing(test_items)
    assert len(diagnoses) == 2

    diag_dict = {d.raw_text: d for d in diagnoses}

    # Verify that the LLM arbitrated the items
    for text, diag in diag_dict.items():
        print(f"Item: '{text}' -> {diag.status} [{diag.hazard_level}] (Tier: {diag.match_tier})")
        print(f"  Reasoning: {diag.regulatory_citation}")

    # Check that at least one item was upgraded to TIER_5_LLM
    has_tier5 = any(d.match_tier == MatchTier.TIER_5_LLM.value for d in diagnoses)
    assert has_tier5 is True


if __name__ == "__main__":
    print("Testing JSON parser robustness...")
    test_llm_json_parser_robustness()
    print("Testing offline graceful fallback...")
    test_llm_offline_graceful_fallback()
    print("Testing live arbitration (if available)...")
    test_live_llm_arbitration_if_available()
    print("All Tier-5 LLM Arbitrator tests passed successfully!")
