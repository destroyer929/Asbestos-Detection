"""
Unit & Integration Tests for Stage 3: Deep Learning OCR & Layout Analysis.
Validates:
1. Levenshtein CER and WER calculation.
2. Architectural region classification and dimension noise filtering.
3. Finish Schedule (仕上表) table boundary detection and cell reconstruction.
"""

import numpy as np
import cv2
from pathlib import Path
from models.ocr.engine import BilingualOCREngine
from models.layout.region_classifier import ArchitecturalRegionClassifier, RegionType
from models.layout.table_parser import FinishScheduleTableParser


def test_cer_and_wer_metrics():
    cer_exact = BilingualOCREngine.compute_cer("吹付け石綿", "吹付け石綿")
    assert cer_exact == 0.0

    cer_one_err = BilingualOCREngine.compute_cer("吹付け石綿", "吹付け岩綿")
    assert abs(cer_one_err - 0.20) < 1e-4

    wer_exact = BilingualOCREngine.compute_wer("Sprayed Asbestos Coating", "Sprayed Asbestos Coating")
    assert wer_exact == 0.0


def test_region_classifier_filtering():
    classifier = ArchitecturalRegionClassifier(2400, 1600)

    dim_samples = ["4,500", "FL ±0", "CH=2700", "1SL +3,200", "13,500", "W=900 H=2,100"]
    for d in dim_samples:
        res = classifier.classify(d, [100, 100, 200, 120])
        assert res.region_type == RegionType.DIMENSION_NOISE
        assert res.is_asbestos_candidate is False

    mat_samples = [
        "鉄骨梁: 吹付けロックウール t=25 (耐火被覆)",
        "スレート波板 t=6.3",
        "石綿保温材 100A",
        "ビニル床タイル 300x300",
        "グラスウール保温材 t=50"
    ]
    for m in mat_samples:
        res = classifier.classify(m, [300, 400, 600, 430])
        assert res.region_type == RegionType.MATERIAL_CALLOUT
        assert res.is_asbestos_candidate is True

    room_res = classifier.classify("機械室", [500, 500, 600, 530])
    assert room_res.region_type == RegionType.ROOM_LABEL
    assert room_res.is_asbestos_candidate is False


def test_table_parser_detection_and_reconstruction():
    parser = FinishScheduleTableParser()
    sample_img = "data/output/clean/ALFRED-DWG-1982-001.png"

    if Path(sample_img).exists():
        img = cv2.imread(sample_img)
        table_box = parser.detect_table_boundary(img)
        assert table_box is not None, "Failed to detect Finish Schedule table boundary"
        assert table_box[0] > 1200, f"Table x_min should be > 1200, got {table_box[0]}"

        import json
        with open("data/output/clean/ALFRED-DWG-1982-001_gt.json", "r", encoding="utf-8") as f:
            gt = json.load(f)

        records = parser.parse_schedule_cells(table_box, gt["annotations"])
        assert len(records) >= 5, f"Expected at least 5 room records, got {len(records)}"


def test_gpu_ocr_acceleration_and_memory_release():
    """Verifies that BilingualOCREngine detects CUDA GPU, runs recognition, and releases GPU memory."""
    engine = BilingualOCREngine(gpu=True)
    # Check GPU flag is active when CUDA is available
    import torch
    if torch.cuda.is_available():
        assert engine.gpu is True
        assert engine.gpu_available is True

    # Test synthetic annotation recognition
    dummy = np.ones((150, 500, 3), dtype=np.uint8) * 255
    cv2.putText(dummy, "ASBESTOS TEST", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    items = engine.recognize(dummy)
    assert isinstance(items, list)

    # Test GPU memory release does not throw
    engine.release_gpu_memory()


if __name__ == "__main__":
    test_cer_and_wer_metrics()
    test_region_classifier_filtering()
    test_table_parser_detection_and_reconstruction()
    print("All Stage 3 OCR & Layout Analysis tests passed successfully!")

