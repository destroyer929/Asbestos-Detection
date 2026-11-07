import json
from pathlib import Path
from core.database.history_manager import BlueprintHistoryManager
from api.server import BENCHMARK_SAMPLES, analyze_sample

history_mgr = BlueprintHistoryManager()

sample_keys = [
    "ALFRED-DWG-1982-001",
    "ALFRED-DWG-1982-002",
    "ALFRED-DWG-1982-003",
    "ALFRED-DWG-1982-004",
    "ALFRED-DWG-1982-005"
]

print("Pre-seeding analysis history database...")
for key in sample_keys:
    try:
        data = analyze_sample(key)
        history_mgr.record_analysis(
            drawing_id=data["drawing_id"],
            filename=data["filename"],
            document_type=data["document_type"],
            is_vector_pdf=data["is_vector_pdf"],
            page_count=data["page_count"],
            summary=data["summary"],
            diagnoses=data["diagnoses"],
            finish_schedule=data["finish_schedule"],
            room_assessments=data.get("room_assessments", []),
            image_base64=data.get("image_base64", ""),
            image_width=data.get("image_width", 2400),
            image_height=data.get("image_height", 1600),
            table_bbox=data.get("table_bbox")
        )
        print(f" - Seeded {key}: {data['summary']['asbestos_positive']} positive, {data['summary']['non_asbestos']} non-asbestos")
    except Exception as e:
        print(f"Error seeding {key}: {e}")

print(f"Seeding complete! Total history records: {len(history_mgr.get_all())}")

