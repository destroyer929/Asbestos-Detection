"""
Unit & Integration Tests for Stage 4: Domain NLP & 4-Tier Matching Engine.
Validates:
1. Unicode NFKC normalization and thickness extraction.
2. SudachiPy morphological analysis and content word isolation.
3. 4-Tier Matching hierarchy (Exact -> Rule -> Fuzzy -> Semantic).
4. 3-State Risk Determination (Positive Level 1/2/3, Negative, Uncertain).
"""

from nlp.normalizer import TextNormalizer
from nlp.tokenizer import JapaneseMorphologicalTokenizer
from nlp.matcher import AsbestosMatchingEngine, MatchTier
from nlp.classifier import AsbestosDiagnosticClassifier


def test_normalizer():
    normalizer = TextNormalizer()

    # 1. Full-width to half-width
    res1 = normalizer.normalize("２５ｍｍ")
    assert res1.cleaned_text == "25mm"
    assert res1.thickness_spec == "t=25"

    # 2. Punctuation stripping
    res2 = normalizer.normalize("【けい酸カルシウム板第１種　ｔ＝８】")
    assert "けい酸カルシウム板第1種" in res2.cleaned_text
    assert res2.thickness_spec == "t=8"


def test_sudachipy_tokenizer():
    tok = JapaneseMorphologicalTokenizer(split_mode="B")
    text = "吹付けロックウール t=25 (耐火被覆)"
    content_words = tok.get_content_words(text)

    # Core architectural content words must be present
    assert any("吹" in w for w in content_words)
    assert any("ロック" in w for w in content_words)


def test_4_tier_matching_engine():
    engine = AsbestosMatchingEngine()

    # Tier 1: Exact Match
    m1 = engine.match("吹付け石綿")
    assert m1.is_positive is True
    assert m1.hazard_level == "LEVEL_1"
    assert m1.match_tier == MatchTier.TIER_1_EXACT
    assert m1.similarity_score == 1.0

    # Tier 2: Domain Rule Match
    m2 = engine.match("鉄骨梁: 吹付けロックウール t=25 (耐火被覆)")
    assert m2.is_positive is True
    assert m2.hazard_level == "LEVEL_1"
    assert m2.match_tier == MatchTier.TIER_2_RULE

    m3 = engine.match("蒸気配管: 石綿保温材 100A")
    assert m3.is_positive is True
    assert m3.hazard_level == "LEVEL_2"
    assert m3.match_tier in (MatchTier.TIER_2_RULE, MatchTier.TIER_1_EXACT)

    m4 = engine.match("スレート波板 t=6.3")
    assert m4.is_positive is True
    assert m4.hazard_level == "LEVEL_3"

    # Non-Asbestos Controls
    m_safe1 = engine.match("グラスウール断熱材 t=50")
    assert m_safe1.is_negative is True
    assert m_safe1.hazard_level == "NON_ASBESTOS"

    m_safe2 = engine.match("せっこうボード t=12.5")
    assert m_safe2.is_negative is True
    assert m_safe2.hazard_level == "NON_ASBESTOS"

    # Tier 3: Fuzzy Match on Typo
    m_fuzzy = engine.match("吹付ロッックウール")
    assert m_fuzzy.is_positive is True
    assert m_fuzzy.match_tier == MatchTier.TIER_3_FUZZY
    assert m_fuzzy.similarity_score >= 0.80

    # Uncertain / Unseen Material
    m_unknown = engine.match("未確認の特殊輸入ボード t=20")
    assert m_unknown.is_uncertain is True
    assert m_unknown.status == "UNCERTAIN"


def test_diagnostic_classifier_end_to_end():
    classifier = AsbestosDiagnosticClassifier()

    items = [
        {"text": "4,500", "bbox": [100, 50, 180, 70]},                              # Dimension -> Ignored
        {"text": "FL ±0", "bbox": [300, 300, 360, 320]},                             # Elevation -> Ignored
        {"text": "鉄骨梁: 吹付けロックウール t=25", "bbox": [150, 180, 450, 210]},     # Level 1 Spray
        {"text": "スレート波板 t=6.3", "bbox": [1400, 350, 1600, 380]},               # Level 3 Slate
        {"text": "グラスウール保温材 t=50", "bbox": [800, 600, 1050, 630]}             # Safe Control
    ]

    results = classifier.diagnose_drawing(items)
    # 2 dimensions filtered out, 3 materials diagnosed
    assert len(results) == 3

    statuses = [r.status for r in results]
    assert statuses.count("POSITIVE") == 2
    assert statuses.count("NEGATIVE") == 1


if __name__ == "__main__":
    test_normalizer()
    test_sudachipy_tokenizer()
    test_4_tier_matching_engine()
    test_diagnostic_classifier_end_to_end()
    print("All Stage 4 NLP & Matching Engine tests passed successfully!")

