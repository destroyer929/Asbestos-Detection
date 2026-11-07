"""
Unit & Integration Tests for Stage 2: Ingestion & Preprocessing Pipeline.
Validates:
1. Vector vs Scanned document routing.
2. Deskew precision on synthetic tilt.
3. Overlapping tiling and Non-Maximum Suppression (NMS) coordinate translation.
"""

import numpy as np
import cv2
from pathlib import Path
from core.ingest.router import DocumentIngestionRouter
from core.preprocess.geometry import GeometryNormalizer
from core.preprocess.tiler import LargeSheetTiler, DetectedBox, ImageTile
from core.preprocess.pipeline import PreprocessingPipeline


def test_document_ingestion_routing():
    router = DocumentIngestionRouter(target_dpi=150)

    # 1. Test Vector PDF
    vec_path = "data/output/pdf_test_suite/ALFRED-DWG-1982-001_vector.pdf"
    if Path(vec_path).exists():
        vec_res = router.ingest(vec_path)
        assert vec_res.doc_type == "VECTOR_PDF"
        assert vec_res.is_vector is True
        assert len(vec_res.vector_entities) > 0

    # 2. Test Scanned PDF
    scan_path = "data/output/pdf_test_suite/ALFRED-DWG-1982-001_scanned.pdf"
    if Path(scan_path).exists():
        scan_res = router.ingest(scan_path)
        assert scan_res.doc_type == "SCANNED_PDF"
        assert scan_res.is_scanned is True
        assert len(scan_res.raster_pages) == 1

    # 3. Test Raw Image
    img_path = "data/output/clean/ALFRED-DWG-1982-001.png"
    if Path(img_path).exists():
        img_res = router.ingest(img_path)
        assert img_res.doc_type == "RASTER_IMAGE"
        assert img_res.is_scanned is True


def test_deskew_precision():
    normalizer = GeometryNormalizer()

    # Create a synthetic canvas with clean horizontal CAD grid lines
    canvas = np.full((1200, 1600), 255, dtype=np.uint8)
    for y in range(200, 1000, 150):
        cv2.line(canvas, (100, y), (1500, y), 0, 3)
    for x in range(200, 1400, 200):
        cv2.line(canvas, (x, 150), (x, 1050), 0, 3)

    # Artificially tilt the canvas by exactly 2.5 degrees
    known_skew = 2.5
    center = (800, 600)
    rot_mat = cv2.getRotationMatrix2D(center, known_skew, 1.0)
    tilted = cv2.warpAffine(canvas, rot_mat, (1600, 1200), borderValue=255)

    # Test detection
    detected_angle = normalizer.detect_skew_angle(tilted)
    error = abs(detected_angle - known_skew)
    assert error < 0.25, f"Deskew error too high: expected {known_skew}, got {detected_angle} (error: {error})"


def test_tiler_and_nms():
    tiler = LargeSheetTiler(tile_size=1000, overlap_ratio=0.20, nms_iou_threshold=0.4)

    dummy_sheet = np.full((2500, 3200, 3), 255, dtype=np.uint8)
    tiles = tiler.tile_image(dummy_sheet)

    # Verify tile dimensions and counts
    assert len(tiles) > 1
    for t in tiles:
        assert t.image.shape == (1000, 1000, 3)
        assert t.x_offset >= 0
        assert t.y_offset >= 0

    # Test NMS coordinate merging on adjacent tiles
    t0 = ImageTile(tile_id=0, image=np.zeros((100, 100)), x_offset=0, y_offset=0, width=1000, height=1000)
    t1 = ImageTile(tile_id=1, image=np.zeros((100, 100)), x_offset=800, y_offset=0, width=1000, height=1000)

    # Box located in overlap region: global [850, 100, 950, 140]
    box_in_t0 = DetectedBox(bbox=[850, 100, 950, 140], confidence=0.92, text="吹付け石綿")
    # Same box in t1 local coords: x - 800 = [50, 100, 150, 140]
    box_in_t1 = DetectedBox(bbox=[50, 100, 150, 140], confidence=0.85, text="吹付け石綿")

    stitched = tiler.stitch_detections([(t0, [box_in_t0]), (t1, [box_in_t1])])
    assert len(stitched) == 1, f"Expected 1 merged box, got {len(stitched)}"
    assert stitched[0].confidence == 0.92
    assert stitched[0].bbox == [850, 100, 950, 140]


def test_adaptive_quality_assessor():
    from core.preprocess.quality_assessor import DocumentQualityAssessor, ProcessingIntensity

    assessor = DocumentQualityAssessor()

    # 1. Clean Canvas (Pristine CAD)
    clean_canvas = np.full((800, 1200), 255, dtype=np.uint8)
    # Add crisp sharp black CAD lines
    cv2.rectangle(clean_canvas, (100, 100), (1100, 700), 0, 2)
    cv2.putText(clean_canvas, "SECTION A-A FINISH SCHEDULE", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, 0, 2)
    q_clean = assessor.assess(clean_canvas, detected_skew_angle=0.0)
    assert q_clean.intensity == ProcessingIntensity.CLEAN_PASSTHROUGH
    assert q_clean.intensity_level == 0
    assert "RAW_IMAGE_PASSTHROUGH" in q_clean.applied_actions

    # 2. Noisy / Degraded Canvas (Simulated Photocopy Smudge)
    noisy_canvas = clean_canvas.copy().astype(np.float32)
    noise = np.random.normal(0, 20.0, noisy_canvas.shape).astype(np.float32)
    noisy_canvas = np.clip(noisy_canvas + noise, 0, 255).astype(np.uint8)
    q_noisy = assessor.assess(noisy_canvas, detected_skew_angle=0.0)
    assert q_noisy.intensity == ProcessingIntensity.AGGRESSIVE_RESTORATION
    assert q_noisy.intensity_level == 2


if __name__ == "__main__":
    test_document_ingestion_routing()
    test_deskew_precision()
    test_tiler_and_nms()
    test_adaptive_quality_assessor()
    print("All Stage 2 preprocessing tests passed successfully!")

