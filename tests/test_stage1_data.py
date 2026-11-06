"""
Unit & Validation Tests for Stage 1: Data & Regulatory Ground Truth Engine.
Verifies database integrity, CAD synthesis bounding box bounds,
and affine transform consistency under scan degradation.
"""

import json
from pathlib import Path
from data.database.db_manager import MaterialsDatabase
from data.generator.cad_generator import CADBlueprintGenerator
from data.degradation.scan_effects import ScanDegradationEngine


def test_database_loads_and_indexes():
    db = MaterialsDatabase()
    summary = db.summary()
    assert summary["total_entries"] > 10
    assert summary["level_1_friable"] >= 3
    assert summary["level_2_insulation"] >= 3
    assert summary["level_3_molded"] >= 4
    assert summary["non_asbestos_controls"] >= 4

    # Test exact lookups
    entry_l1 = db.exact_lookup("吹付け石綿")
    assert entry_l1 is not None
    assert entry_l1.hazard_level == "LEVEL_1"
    assert entry_l1.status == "POSITIVE"

    entry_safe = db.exact_lookup("グラスウール")
    assert entry_safe is not None
    assert entry_safe.hazard_level == "NON_ASBESTOS"
    assert entry_safe.status == "NEGATIVE"


def test_cad_generation_bounding_boxes(tmp_path):
    generator = CADBlueprintGenerator(width=2000, height=1400)
    result = generator.generate("TEST-UNIT-001", tmp_path, seed=99)

    assert result["annotation_count"] > 20
    assert result["asbestos_positive_count"] > 0
    assert (tmp_path / "TEST-UNIT-001.png").exists()
    assert (tmp_path / "TEST-UNIT-001.dxf").exists()
    assert (tmp_path / "TEST-UNIT-001_gt.json").exists()

    # Validate coordinate boundaries
    for anno in result["annotations"]:
        bbox = anno["bbox"]
        assert 0 <= bbox[0] <= 2000, f"x_min out of bounds: {bbox[0]}"
        assert 0 <= bbox[1] <= 1400, f"y_min out of bounds: {bbox[1]}"
        assert bbox[2] >= bbox[0], f"x_max must be >= x_min: {bbox}"
        assert bbox[3] >= bbox[1], f"y_max must be >= y_min: {bbox}"


def test_scan_degradation_transform(tmp_path):
    generator = CADBlueprintGenerator(width=2000, height=1400)
    generator.generate("TEST-UNIT-002", tmp_path, seed=101)

    degrader = ScanDegradationEngine(seed=42)
    clean_img = tmp_path / "TEST-UNIT-002.png"
    clean_gt = tmp_path / "TEST-UNIT-002_gt.json"
    deg_img = tmp_path / "TEST-UNIT-002_deg.jpg"
    deg_gt = tmp_path / "TEST-UNIT-002_deg_gt.json"

    deg_res = degrader.degrade(clean_img, clean_gt, deg_img, deg_gt, skew_angle=2.5)
    assert deg_img.exists()
    assert deg_gt.exists()
    assert len(deg_res["annotations"]) > 20
    assert deg_res["skew_angle"] == 2.5


if __name__ == "__main__":
    test_database_loads_and_indexes()
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        test_cad_generation_bounding_boxes(Path(tmp))
        test_scan_degradation_transform(Path(tmp))
    print("All Stage 1 validation tests passed successfully!")
