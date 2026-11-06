"""
Unit & Integration Tests for Stage 5: FastAPI Service & Human Review Workflow.
Validates:
1. Health check & database summary endpoints.
2. Preset benchmark samples listing & direct analysis endpoints.
3. Human-in-the-Loop review override recording & history retrieval.
4. Full end-to-end PDF analysis endpoint (/api/v1/analyze).
"""

from pathlib import Path
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


def test_api_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["database_entries"] >= 10
    print("[PASS] Health check endpoint verified")


def test_api_database_summary():
    res = client.get("/api/v1/database/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["level_1_friable"] >= 3
    assert data["level_2_insulation"] >= 3
    assert data["level_3_molded"] >= 4
    assert data["indexed_lookup_keys"] >= 100
    print("[PASS] Database summary endpoint verified")


def test_api_samples():
    res = client.get("/api/v1/samples")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 3
    assert any(s["id"] == "ALFRED-DWG-1982-001" for s in data)
    print("[PASS] Benchmark preset samples list verified")


def test_api_analyze_sample():
    res = client.post("/api/v1/samples/ALFRED-DWG-1982-001/analyze")
    assert res.status_code == 200
    data = res.json()
    assert data["drawing_id"] == "ALFRED-DWG-1982-001"
    assert "summary" in data
    assert data["summary"]["asbestos_positive"] >= 1
    assert "image_base64" in data
    assert data["image_base64"].startswith("data:image/jpeg;base64,")
    assert data["image_width"] > 0
    assert data["image_height"] > 0
    assert len(data["diagnoses"]) > 0
    print(f"[PASS] Preset sample analysis verified: {len(data['diagnoses'])} items detected, dimensions {data['image_width']}x{data['image_height']}")


def test_api_human_override():
    payload = {
        "item_id": "ITEM-TEST-UNIT-99",
        "drawing_id": "DWG-1982-001",
        "corrected_status": "POSITIVE",
        "corrected_hazard_level": "LEVEL_1",
        "corrected_material_name": "吹付け石綿",
        "reviewer_notes": "Verified by certified inspector"
    }
    res = client.post("/api/v1/review/override", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "total_active_learning_samples" in data
    print("[PASS] Human override recording verified")


def test_api_review_history():
    res = client.get("/api/v1/review/history")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "corrections" in data
    assert data["total"] >= 1
    print(f"[PASS] Active learning history verified: {data['total']} logged corrections")


def test_api_download_endpoints():
    res_list = client.get("/api/v1/download/available")
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data) >= 5
    print(f"[PASS] Available download catalog verified: {len(data)} downloadable assets")

    res_file = client.get("/api/v1/download/sample/ALFRED-DWG-1982-004_scanned.pdf")
    assert res_file.status_code == 200
    assert len(res_file.content) > 100000
    print(f"[PASS] Sample download endpoint verified: received {len(res_file.content)} bytes")


def test_api_analyze_vector_pdf():
    pdf_path = Path("data/output/pdf_test_suite/ALFRED-DWG-1982-001_vector.pdf")
    if pdf_path.exists():
        with open(pdf_path, "rb") as f:
            res = client.post("/api/v1/analyze", files={"file": ("drawing.pdf", f, "application/pdf")})

        assert res.status_code == 200
        data = res.json()
        assert data["document_type"] == "VECTOR_PDF"
        assert "summary" in data
        assert "asbestos_positive" in data["summary"]
        assert len(data["diagnoses"]) > 0
        print(f"[PASS] Vector PDF upload & analysis verified: {len(data['diagnoses'])} items")


if __name__ == "__main__":
    test_api_health()
    test_api_database_summary()
    test_api_samples()
    test_api_analyze_sample()
    test_api_human_override()
    test_api_review_history()
    test_api_download_endpoints()
    test_api_analyze_vector_pdf()
    print("\nALL STAGE 5 API ENDPOINTS AND REVIEW WORKFLOW TESTS PASSED 100%!")
