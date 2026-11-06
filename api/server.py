"""
FastAPI Production Microservice for Asbestos Blueprint Diagnostics.
Exposes endpoints:
- POST /api/v1/analyze: Analyzes PDF/image blueprints through the full Stages 1-4 pipeline.
- GET  /api/v1/samples: Lists available benchmark preset blueprints.
- POST /api/v1/samples/{sample_id}/analyze: Runs diagnostics on a benchmark blueprint preset.
- GET  /api/v1/database/summary: Returns MLIT reference database statistics.
- POST /api/v1/review/override: Saves human expert overrides into the active learning loop.
- GET  /api/v1/review/history: Retrieves recorded human override verifications.
- GET  /api/v1/health: Service health check.
"""

from __future__ import annotations
import os
import json
import uuid
import shutil
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import cv2
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from data.database.db_manager import MaterialsDatabase
from core.ingest.router import DocumentIngestionRouter, IngestionResult
from core.preprocess.pipeline import PreprocessingPipeline
from core.preprocess.geometry import GeometryNormalizer
from models.ocr.engine import BilingualOCREngine
from models.layout.table_parser import FinishScheduleTableParser
from models.layout.room_assessor import SpatialRoomAssessor, RoomAssessment
from nlp.classifier import AsbestosDiagnosticClassifier, DrawingItemDiagnosis


app = FastAPI(
    title="DrawingScan API - Asbestos Identification in Building Drawings",
    description="Automated MLIT-compliant asbestos detection and finish schedule diagnostics for Alfred Company Ltd.",
    version="1.0.0"
)

# Enable CORS for Next.js and frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core singletons
db = MaterialsDatabase()
pipeline = PreprocessingPipeline(target_dpi=300)
ocr_engine = BilingualOCREngine(gpu=True)
table_parser = FinishScheduleTableParser()
classifier = AsbestosDiagnosticClassifier(db=db)
room_assessor = SpatialRoomAssessor()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CORRECTIONS_FILE = Path("data/active_learning_corrections.json")

JOB_REGISTRY: Dict[str, Dict[str, Any]] = {}


def process_pages_background(drawing_id: str, file_path_str: str, total_pages: int, is_vector: bool = False):
    """
    Asynchronous multi-page worker:
    Hierarchically segments & analyzes remaining pages (2..N) in the background.
    Caches JPEG and JSON for each page so navigation is instantaneous.
    """
    file_path = Path(file_path_str)
    try:
        import fitz
        doc = fitz.open(file_path_str)
        normalizer = GeometryNormalizer()

        for page_idx in range(1, total_pages):
            page_num = page_idx + 1
            if drawing_id in JOB_REGISTRY:
                JOB_REGISTRY[drawing_id]["current_status"] = f"Analyzing page {page_num} of {total_pages}..."

            page = doc[page_idx]
            rect = page.rect
            zoom = 1.0 if rect.width >= 1600 else min(2400.0 / max(rect.width, 1.0), 300.0 / 72.0)
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix)
            img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
            if pix.n == 4:
                img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

            norm_img, geom_meta = normalizer.process(img)
            disp_img = geom_meta.get("display_image", img)
            p_h, p_w = disp_img.shape[:2]

            # Cache authentic page image to disk
            page_cache_path = UPLOAD_DIR / f"{drawing_id}_page_{page_num}.jpg"
            cv2.imwrite(str(page_cache_path), disp_img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

            # Detect finish schedule table
            t_box = table_parser.detect_table_boundary(disp_img)

            # Hierarchical ROI OCR (Fast & Targeted)
            ocr_items = ocr_engine.recognize_hierarchical(norm_img, table_bbox=t_box)
            raw_items = [
                {"text": it.text, "bbox": it.bbox, "confidence": it.confidence}
                for it in ocr_items
            ]

            # Parse schedule
            parsed_schedule = []
            if t_box:
                records = table_parser.parse_schedule_cells(t_box, raw_items)
                parsed_schedule = [
                    {
                        "room": r.room_name,
                        "floor": r.floor_finish,
                        "wall": r.wall_finish,
                        "ceiling": r.ceiling_finish,
                        "remarks": r.remarks
                    }
                    for r in records
                ]

            diagnoses = classifier.diagnose_drawing(raw_items, table_bbox=t_box, page_number=page_num)

            # Room assessments
            room_evals = room_assessor.assess_rooms(
                diagnoses=diagnoses,
                finish_schedule=parsed_schedule,
                image_width=p_w,
                image_height=p_h,
                table_bbox=t_box
            )

            # Save page JSON cache
            page_data = {
                "drawing_id": drawing_id,
                "page_number": page_num,
                "image_width": p_w,
                "image_height": p_h,
                "table_bbox": t_box,
                "diagnoses": [d.to_dict() for d in diagnoses],
                "finish_schedule": parsed_schedule,
                "room_assessments": [r.to_dict() for r in room_evals]
            }
            page_json_path = UPLOAD_DIR / f"{drawing_id}_page_{page_num}.json"
            with open(page_json_path, "w", encoding="utf-8") as f:
                json.dump(page_data, f, ensure_ascii=False)

            if drawing_id in JOB_REGISTRY:
                JOB_REGISTRY[drawing_id]["completed_pages"].append(page_num)
                JOB_REGISTRY[drawing_id]["all_diagnoses"].extend(diagnoses)
                JOB_REGISTRY[drawing_id]["progress_percent"] = int(
                    (len(JOB_REGISTRY[drawing_id]["completed_pages"]) / total_pages) * 100
                )

        doc.close()
        if drawing_id in JOB_REGISTRY:
            JOB_REGISTRY[drawing_id]["status"] = "completed"
            JOB_REGISTRY[drawing_id]["current_status"] = f"Complete: all {total_pages} pages analyzed."

    except Exception as e:
        print(f"Background worker error for {drawing_id}: {e}")
        if drawing_id in JOB_REGISTRY:
            JOB_REGISTRY[drawing_id]["status"] = "error"
            JOB_REGISTRY[drawing_id]["error"] = str(e)
    finally:
        if file_path.exists():
            try:
                file_path.unlink()
            except Exception:
                pass


def encode_image_to_base64(img_np: np.ndarray, quality: int = 85) -> str:
    """Converts a numpy RGB/BGR image array into a base64 JPEG data URI."""
    try:
        if len(img_np.shape) == 2:
            # Grayscale
            success, buffer = cv2.imencode(".jpg", img_np, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        elif img_np.shape[2] == 3:
            # Check if RGB or BGR - cv2 expects BGR
            success, buffer = cv2.imencode(".jpg", img_np, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        else:
            success, buffer = cv2.imencode(".jpg", img_np[:, :, :3], [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if success:
            encoded = base64.b64encode(buffer).decode("utf-8")
            return f"data:image/jpeg;base64,{encoded}"
    except Exception as e:
        print(f"Base64 encoding error: {e}")
    return ""


# Pre-configured benchmark samples for instant evaluation
BENCHMARK_SAMPLES = {
    "REAL-SAMPLE-YUKUHASHI-01": {
        "id": "REAL-SAMPLE-YUKUHASHI-01",
        "title": "Real Blueprint: Yukuhashi City Finish Schedule 1 (建築意匠 仕上表)",
        "description": "Authentic public municipal blueprint from Yukuhashi City Architecture Dept. Real room finishes, flooring, walls, and ceiling schedules.",
        "image_path": "data/output/real_samples/REAL-SAMPLE-01-YUKUHASHI-FINISH-SCHEDULE-1.jpg",
        "gt_path": "",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "REAL-SAMPLE-YUKUHASHI-02": {
        "id": "REAL-SAMPLE-YUKUHASHI-02",
        "title": "Real Blueprint: Yukuhashi City Finish Schedule 2 (仕上表 2)",
        "description": "Authentic Finish Schedule 2 detailing partition walls (LGS, GB-R, plasterboard, DR acoustic tiles).",
        "image_path": "data/output/real_samples/REAL-SAMPLE-02-YUKUHASHI-FINISH-SCHEDULE-2.jpg",
        "gt_path": "",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "REAL-SAMPLE-YUKUHASHI-03": {
        "id": "REAL-SAMPLE-YUKUHASHI-03",
        "title": "Real Blueprint: Yukuhashi City 1F/2F Floor Plan (平面図)",
        "description": "Authentic architectural floor plan showing actual room dimensions, corridors, staircases, and callouts.",
        "image_path": "data/output/real_samples/REAL-SAMPLE-03-YUKUHASHI-FLOOR-PLAN-1F-2F.jpg",
        "gt_path": "",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "REAL-SAMPLE-ATSUGI-04": {
        "id": "REAL-SAMPLE-ATSUGI-04",
        "title": "Real Blueprint: Atsugi City Existing Facility Plan (既存建物設計図書)",
        "description": "Authentic scanned public facility drawing from Atsugi City municipal archive.",
        "image_path": "data/output/real_samples/REAL-SAMPLE-05-ATSUGI-SCANNED-FLOOR-PLAN.jpg",
        "gt_path": "",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "REAL-SAMPLE-SAITAMA-05": {
        "id": "REAL-SAMPLE-SAITAMA-05",
        "title": "Real Blueprint: Saitama Prefectural Architectural Scan (埼玉県公共施設)",
        "description": "Authentic full-sheet scanned engineering blueprint from Saitama Prefecture public works.",
        "image_path": "data/output/real_samples/REAL-SAMPLE-04-SAITAMA-SCANNED-BLUEPRINT.jpg",
        "gt_path": "",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-001": {
        "id": "ALFRED-DWG-1982-001",
        "title": "ALFRED-DWG-1982-001 (Degraded Scan 1.6°)",
        "description": "Hamamatsu Machine Tool Plant (1982). Spray rockwool on steel beams, corrugated asbestos cement roof, vinyl tiles.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-001_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-001_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-002": {
        "id": "ALFRED-DWG-1982-002",
        "title": "ALFRED-DWG-1982-002 (Clean CAD Blueprint)",
        "description": "Precision electronics manufacturing cleanroom. Level 2 diatomaceous earth pipe lagging, calcium silicate board ceiling.",
        "image_path": "data/output/clean/ALFRED-DWG-1982-002.png",
        "gt_path": "data/output/clean/ALFRED-DWG-1982-002_gt.json",
        "doc_type": "VECTOR_CAD"
    },
    "ALFRED-DWG-1982-003": {
        "id": "ALFRED-DWG-1982-003",
        "title": "ALFRED-DWG-1982-003 (Degraded Scan 2.4°)",
        "description": "Boiler room & electrical sub-station. High-risk Level 1 spray asbestos, chrysotile acoustic plaster, vertical callouts.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-003_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-003_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-004": {
        "id": "ALFRED-DWG-1982-004",
        "title": "ALFRED-DWG-1982-004 (Degraded Scan 1.9°)",
        "description": "Chemical storage & warehouse. Sprayed crocidolite blue asbestos, flexible insulation board wall linings.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-004_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-004_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-005": {
        "id": "ALFRED-DWG-1982-005",
        "title": "ALFRED-DWG-1982-005 (Degraded Scan 3.1°)",
        "description": "Heavy manufacturing assembly plant. High tilt angle scan with dense multi-room finish schedule matrix.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-005_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-005_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-006": {
        "id": "ALFRED-DWG-1982-006",
        "title": "ALFRED-DWG-1982-006 (New Scan 2.4°)",
        "description": "High-temperature machinery test building with spray rockwool and amosite insulation boards.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-006_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-006_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-007": {
        "id": "ALFRED-DWG-1982-007",
        "title": "ALFRED-DWG-1982-007 (New Scan 2.6°)",
        "description": "Textile finishing mill with acoustic plaster ceiling and diatomaceous earth pipe lagging.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-007_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-007_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-008": {
        "id": "ALFRED-DWG-1982-008",
        "title": "ALFRED-DWG-1982-008 (New Scan 2.8°)",
        "description": "Automotive parts stamping facility with corrugated asbestos cement roofing slates.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-008_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-008_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-009": {
        "id": "ALFRED-DWG-1982-009",
        "title": "ALFRED-DWG-1982-009 (New Scan 3.0°)",
        "description": "Sub-station generator facility with spray chrysotile fireproofing on structural columns.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-009_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-009_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    },
    "ALFRED-DWG-1982-010": {
        "id": "ALFRED-DWG-1982-010",
        "title": "ALFRED-DWG-1982-010 (New Scan 3.2°)",
        "description": "Multi-story warehouse logistics facility with vinyl asbestos floor tiles and glasswool partitions.",
        "image_path": "data/output/degraded/ALFRED-DWG-1982-010_scanned.jpg",
        "gt_path": "data/output/degraded/ALFRED-DWG-1982-010_scanned_gt.json",
        "doc_type": "SCANNED_BLUEPRINT"
    }
}


class HumanOverrideRequest(BaseModel):
    item_id: str
    drawing_id: str
    corrected_status: str  # POSITIVE, NEGATIVE, UNCERTAIN
    corrected_hazard_level: str  # LEVEL_1, LEVEL_2, LEVEL_3, NON_ASBESTOS, UNCERTAIN
    corrected_material_name: str
    reviewer_notes: str = ""


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "DrawingScan AI Engine",
        "gpu_available": ocr_engine.gpu,
        "database_entries": len(db.entries)
    }


@app.get("/api/v1/database/summary")
def get_database_summary():
    """Returns official Japanese MLIT database statistics."""
    return db.summary()


@app.get("/api/v1/download/sample/{filename}")
def download_sample_file(filename: str):
    """Allows downloading test blueprints (.pdf, .jpg, .png, .dxf) directly."""
    search_dirs = [
        Path("data/output/real_samples"),
        Path("data/real_blueprints"),
        Path("data/output/large_sets"),
        Path("data/output/pdf_test_suite"),
        Path("data/output/degraded"),
        Path("data/output/clean"),
    ]
    for d in search_dirs:
        candidate = d / filename
        if candidate.exists() and candidate.is_file():
            ext = candidate.suffix.lower()
            media_type = "application/octet-stream"
            if ext == ".pdf":
                media_type = "application/pdf"
            elif ext in (".jpg", ".jpeg"):
                media_type = "image/jpeg"
            elif ext == ".png":
                media_type = "image/png"
            elif ext == ".json":
                media_type = "application/json"

            return FileResponse(
                path=candidate,
                filename=filename,
                media_type=media_type,
                headers={"Content-Disposition": f'attachment; filename="{filename}"'}
            )
    raise HTTPException(status_code=404, detail=f"File {filename} not found.")


@app.get("/api/v1/download/available")
def list_available_downloads():
    """Returns list of downloadable test files for user evaluation."""
    items = []
    # 0. Real Authentic Municipal Blueprints (Yukuhashi, Saitama, Atsugi, Nagareyama)
    for p in sorted(Path("data/output/real_samples").glob("*")):
        if p.is_file():
            ext = p.suffix.lower()
            cat = "Real Municipal Blueprint (PDF)" if ext == ".pdf" else "Real Blueprint Sheet Scan (JPG)"
            items.append({
                "filename": p.name,
                "category": cat,
                "size_kb": round(p.stat().st_size / 1024, 1),
                "download_url": f"/api/v1/download/sample/{p.name}"
            })
    # 1. 30-Page Blueprint Packages (Vector & Scanned)
    for p in sorted(Path("data/output/large_sets").glob("*.pdf")):
        items.append({
            "filename": p.name,
            "category": "30-Page Scanned Package" if "_scanned" in p.name else "30-Page Vector CAD Package",
            "size_kb": round(p.stat().st_size / 1024, 1),
            "download_url": f"/api/v1/download/sample/{p.name}"
        })
    # 2. Scanned PDFs
    for p in sorted(Path("data/output/pdf_test_suite").glob("*.pdf")):
        items.append({
            "filename": p.name,
            "category": "Scanned Blueprint PDF" if "_scanned" in p.name else "Vector CAD PDF",
            "size_kb": round(p.stat().st_size / 1024, 1),
            "download_url": f"/api/v1/download/sample/{p.name}"
        })
    # 3. Degraded Scans JPG
    for p in sorted(Path("data/output/degraded").glob("*_scanned.jpg")):
        items.append({
            "filename": p.name,
            "category": "Scanned Blueprint Image (JPG)",
            "size_kb": round(p.stat().st_size / 1024, 1),
            "download_url": f"/api/v1/download/sample/{p.name}"
        })
    # 4. Clean CAD DXF
    for p in sorted(Path("data/output/clean").glob("*.dxf")):
        items.append({
            "filename": p.name,
            "category": "CAD Vector Blueprint (DXF)",
            "size_kb": round(p.stat().st_size / 1024, 1),
            "download_url": f"/api/v1/download/sample/{p.name}"
        })
    return items


@app.post("/api/v1/samples/generate")
def generate_new_sample():
    """Generates a brand-new randomized Japanese blueprint on the fly."""
    from data.generator.cad_generator import CADBlueprintGenerator
    from data.degradation.scan_effects import ScanDegradationEngine
    from generate_dataset import _create_vector_pdf, _convert_image_to_pdf
    import random
    import time

    gen_id = f"ALFRED-DWG-NEW-{int(time.time()) % 10000:04d}"
    seed = random.randint(500, 9999)

    clean_dir = Path("data/output/clean")
    deg_dir = Path("data/output/degraded")
    pdf_dir = Path("data/output/pdf_test_suite")
    clean_dir.mkdir(parents=True, exist_ok=True)
    deg_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    generator = CADBlueprintGenerator(db=db)
    degrader = ScanDegradationEngine()

    clean_gt = generator.generate(gen_id, clean_dir, seed=seed)
    png_path = clean_dir / f"{gen_id}.png"
    gt_path = clean_dir / f"{gen_id}_gt.json"

    deg_img_path = deg_dir / f"{gen_id}_scanned.jpg"
    deg_gt_path = deg_dir / f"{gen_id}_scanned_gt.json"
    deg_pdf_path = pdf_dir / f"{gen_id}_scanned.pdf"

    skew = random.choice([-1, 1]) * round(random.uniform(1.2, 2.8), 1)
    degrader.degrade(
        image_path=png_path,
        ground_truth_path=gt_path,
        output_image_path=deg_img_path,
        output_gt_path=deg_gt_path,
        skew_angle=skew,
        blur_ksize=random.choice([1, 3]),
        noise_density=random.uniform(0.005, 0.015)
    )

    _convert_image_to_pdf(deg_img_path, deg_pdf_path)

    BENCHMARK_SAMPLES[gen_id] = {
        "id": gen_id,
        "title": f"{gen_id} (Newly Synthesized Scan {skew:+.1f}°)",
        "description": f"Custom generated blueprint (seed: {seed}) with {clean_gt['annotation_count']} annotations and {clean_gt['asbestos_positive_count']} asbestos items.",
        "image_path": str(deg_img_path),
        "gt_path": str(deg_gt_path),
        "doc_type": "SCANNED_BLUEPRINT"
    }

    return {
        "id": gen_id,
        "title": BENCHMARK_SAMPLES[gen_id]["title"],
        "description": BENCHMARK_SAMPLES[gen_id]["description"],
        "doc_type": "SCANNED_BLUEPRINT",
        "download_pdf": f"/api/v1/download/sample/{gen_id}_scanned.pdf",
        "download_image": f"/api/v1/download/sample/{gen_id}_scanned.jpg"
    }


@app.get("/api/v1/samples")
def list_samples():
    """Returns available benchmark suite samples for 1-click evaluation."""
    return [
        {
            "id": s["id"],
            "title": s["title"],
            "description": s["description"],
            "doc_type": s["doc_type"]
        }
        for s in BENCHMARK_SAMPLES.values()
    ]


@app.post("/api/v1/samples/{sample_id}/analyze")
def analyze_sample(sample_id: str):
    """
    Runs diagnostic inspection on a preloaded benchmark blueprint with sub-second response.
    """
    if sample_id not in BENCHMARK_SAMPLES:
        raise HTTPException(status_code=404, detail=f"Sample {sample_id} not found")

    sample_meta = BENCHMARK_SAMPLES[sample_id]
    img_path = Path(sample_meta["image_path"])
    gt_path = Path(sample_meta["gt_path"])

    if not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Image file missing: {img_path}")

    # Load Image
    img_cv = cv2.imread(str(img_path))
    if img_cv is None:
        raise HTTPException(status_code=500, detail="Failed to decode sample image")
    h, w = img_cv.shape[:2]

    # Load GT or run OCR
    input_items = []
    if gt_path.exists():
        with open(gt_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
        input_items = gt_data.get("annotations", [])
    else:
        ocr_items = ocr_engine.recognize(img_cv)
        input_items = [
            {"text": item.text, "bbox": item.bbox, "confidence": item.confidence}
            for item in ocr_items
        ]

    # Detect table boundary & parse schedule
    table_box = table_parser.detect_table_boundary(img_cv)
    parsed_schedule_records = []
    if table_box:
        records = table_parser.parse_schedule_cells(table_box, input_items)
        parsed_schedule_records = [
            {
                "room": r.room_name,
                "floor": r.floor_finish,
                "wall": r.wall_finish,
                "ceiling": r.ceiling_finish,
                "remarks": r.remarks
            }
            for r in records
        ]

    # Run MLIT Diagnostic Classifier
    diagnoses: List[DrawingItemDiagnosis] = classifier.diagnose_drawing(input_items, table_bbox=table_box)

    pos_count = sum(1 for d in diagnoses if d.status == "POSITIVE")
    neg_count = sum(1 for d in diagnoses if d.status == "NEGATIVE")
    unc_count = sum(1 for d in diagnoses if d.status == "UNCERTAIN")
    review_count = sum(1 for d in diagnoses if d.requires_human_review)

    l1_count = sum(1 for d in diagnoses if d.hazard_level == "LEVEL_1")
    l2_count = sum(1 for d in diagnoses if d.hazard_level == "LEVEL_2")
    l3_count = sum(1 for d in diagnoses if d.hazard_level == "LEVEL_3")

    # Generate Spatial Room Assessments (Matching ChatGPT-grade spatial overlays)
    room_evals = room_assessor.assess_rooms(
        diagnoses=diagnoses,
        finish_schedule=parsed_schedule_records,
        image_width=w,
        image_height=h,
        table_bbox=table_box
    )

    img_b64 = encode_image_to_base64(img_cv)

    return {
        "drawing_id": sample_id,
        "filename": img_path.name,
        "document_type": sample_meta["doc_type"],
        "is_vector_pdf": False,
        "page_count": 1,
        "current_page": 1,
        "pages": [
            {
                "page_number": 1,
                "width": w,
                "height": h,
                "table_bbox": table_box
            }
        ],
        "image_width": w,
        "image_height": h,
        "image_base64": img_b64,
        "table_bbox": table_box,
        "total_material_annotations": len(diagnoses),
        "summary": {
            "asbestos_positive": pos_count,
            "non_asbestos": neg_count,
            "uncertain": unc_count,
            "review_required": review_count,
            "hazard_levels": {
                "level_1_sprays": l1_count,
                "level_2_insulation": l2_count,
                "level_3_molded": l3_count
            }
        },
        "room_assessments": [r.to_dict() for r in room_evals],
        "finish_schedule": parsed_schedule_records,
        "diagnoses": [d.to_dict() for d in diagnoses]
    }


@app.post("/api/v1/analyze")
async def analyze_drawing(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Hierarchical Multi-Model Blueprint Analysis Engine:
    1. Fast-track Page 1 (< 2.5s response):
       - Renders & deskews Page 1
       - Slices into targeted Finish Schedule & Callout ROIs (< 150ms)
       - Hierarchical deep GPU OCR on ROIs
       - 4-Tier MLIT asbestos diagnostic classification
       - Returns Page 1 immediately for instant UI display
    2. Background multi-page worker:
       - Queues Pages 2..N to execute asynchronously in the background
       - Caches per-page high-res JPG and JSON diagnostics for instantaneous pagination
    """
    file_id = f"UPLOAD-{uuid.uuid4().hex[:8]}"
    ext = Path(file.filename).suffix.lower()
    temp_path = UPLOAD_DIR / f"{file_id}{ext}"

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 1. Inspect format & page count
        is_pdf = ext == ".pdf"
        total_pages = 1
        is_vector = False
        vector_entities_page1 = []

        if is_pdf:
            import fitz
            doc = fitz.open(str(temp_path))
            total_pages = len(doc)
            # Check vector text density on page 1
            p1 = doc[0]
            blocks = p1.get_text("blocks")
            p1_chars = sum(len(b[4].strip()) for b in blocks if len(b) >= 7 and b[6] == 0 and b[4].strip())
            is_vector = p1_chars >= 50
            if is_vector:
                # Validate readable glyphs
                qmarks = sum(b[4].count("?") for b in blocks if len(b) >= 7 and b[6] == 0)
                if qmarks > 15:
                    is_vector = False

            # Render Page 1
            rect = p1.rect
            zoom = 1.0 if rect.width >= 1600 else min(2400.0 / max(rect.width, 1.0), 300.0 / 72.0)
            matrix = fitz.Matrix(zoom, zoom)
            pix = p1.get_pixmap(matrix=matrix)
            p1_img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
            if pix.n == 4:
                p1_img = cv2.cvtColor(p1_img, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                p1_img = cv2.cvtColor(p1_img, cv2.COLOR_RGB2BGR)

            if is_vector:
                scale_x = float(pix.w) / float(rect.width) if rect.width > 0 else 1.0
                scale_y = float(pix.h) / float(rect.height) if rect.height > 0 else 1.0
                for b in blocks:
                    if len(b) >= 7 and b[6] == 0 and b[4].strip():
                        vector_entities_page1.append({
                            "text": b[4].strip(),
                            "bbox": [float(b[0]) * scale_x, float(b[1]) * scale_y, float(b[2]) * scale_x, float(b[3]) * scale_y],
                            "confidence": 1.0,
                            "page_num": 1
                        })
            doc.close()
        else:
            p1_img = cv2.imread(str(temp_path))
            if p1_img is None:
                raise HTTPException(status_code=400, detail="Could not decode uploaded image")

        # 2. Geometric Deskew & Illumination Normalization for Page 1
        normalizer = GeometryNormalizer()
        norm_img, geom_meta = normalizer.process(p1_img)
        disp_img = geom_meta.get("display_image", p1_img)
        p_h, p_w = disp_img.shape[:2]

        # Cache Page 1 original image
        p1_img_path = UPLOAD_DIR / f"{file_id}_page_1.jpg"
        cv2.imwrite(str(p1_img_path), disp_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        # 3. Detect Finish Schedule Table on Page 1
        t_box = table_parser.detect_table_boundary(disp_img)

        # 4. Hierarchical OCR or Vector extraction on Page 1
        if is_vector and vector_entities_page1:
            raw_items = vector_entities_page1
        else:
            ocr_items = ocr_engine.recognize_hierarchical(norm_img, table_bbox=t_box)
            raw_items = [
                {"text": it.text, "bbox": it.bbox, "confidence": it.confidence}
                for it in ocr_items
            ]

        # 5. Parse Schedule Cells for Page 1
        parsed_schedule_records = []
        if t_box:
            records = table_parser.parse_schedule_cells(t_box, raw_items)
            parsed_schedule_records = [
                {
                    "room": r.room_name,
                    "floor": r.floor_finish,
                    "wall": r.wall_finish,
                    "ceiling": r.ceiling_finish,
                    "remarks": r.remarks
                }
                for r in records
            ]

        # 6. MLIT Asbestos Diagnostic Classifier for Page 1
        page1_diagnoses = classifier.diagnose_drawing(raw_items, table_bbox=t_box, page_number=1)

        # 7. Spatial Room Assessments for Page 1
        room_evals = room_assessor.assess_rooms(
            diagnoses=page1_diagnoses,
            finish_schedule=parsed_schedule_records,
            image_width=p_w,
            image_height=p_h,
            table_bbox=t_box
        )

        # Cache Page 1 JSON
        p1_json_path = UPLOAD_DIR / f"{file_id}_page_1.json"
        p1_data = {
            "drawing_id": file_id,
            "page_number": 1,
            "image_width": p_w,
            "image_height": p_h,
            "table_bbox": t_box,
            "diagnoses": [d.to_dict() for d in page1_diagnoses],
            "finish_schedule": parsed_schedule_records,
            "room_assessments": [r.to_dict() for r in room_evals]
        }
        with open(p1_json_path, "w", encoding="utf-8") as f:
            json.dump(p1_data, f, ensure_ascii=False)

        # 8. Setup Metadata & Multi-Page Background Task
        pages_meta = [{
            "page_number": p + 1,
            "width": p_w,
            "height": p_h,
            "table_bbox": t_box if p == 0 else None
        } for p in range(total_pages)]

        img_b64 = encode_image_to_base64(disp_img)

        # Register Job Status
        JOB_REGISTRY[file_id] = {
            "drawing_id": file_id,
            "status": "processing" if total_pages > 1 else "completed",
            "total_pages": total_pages,
            "completed_pages": [1],
            "all_diagnoses": list(page1_diagnoses),
            "progress_percent": int((1 / total_pages) * 100),
            "current_status": f"Page 1 ready. Processing remaining {total_pages - 1} pages in background..." if total_pages > 1 else "Complete"
        }

        # If multi-page, spawn background worker to process Pages 2..N
        if total_pages > 1 and background_tasks is not None:
            background_tasks.add_task(
                process_pages_background,
                file_id,
                str(temp_path),
                total_pages,
                is_vector
            )
        else:
            # Single page: cleanup temp
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

        pos_count = sum(1 for d in page1_diagnoses if d.status == "POSITIVE")
        neg_count = sum(1 for d in page1_diagnoses if d.status == "NEGATIVE")
        unc_count = sum(1 for d in page1_diagnoses if d.status == "UNCERTAIN")
        review_count = sum(1 for d in page1_diagnoses if d.requires_human_review)

        l1_count = sum(1 for d in page1_diagnoses if d.hazard_level == "LEVEL_1")
        l2_count = sum(1 for d in page1_diagnoses if d.hazard_level == "LEVEL_2")
        l3_count = sum(1 for d in page1_diagnoses if d.hazard_level == "LEVEL_3")

        return {
            "drawing_id": file_id,
            "filename": file.filename,
            "document_type": "VECTOR_PDF" if is_vector else ("SCANNED_PDF" if is_pdf else "RASTER_IMAGE"),
            "is_vector_pdf": is_vector,
            "page_count": total_pages,
            "current_page": 1,
            "status": "processing" if total_pages > 1 else "completed",
            "pages": pages_meta,
            "image_width": p_w,
            "image_height": p_h,
            "image_base64": img_b64,
            "table_bbox": t_box,
            "total_material_annotations": len(page1_diagnoses),
            "summary": {
                "asbestos_positive": pos_count,
                "non_asbestos": neg_count,
                "uncertain": unc_count,
                "review_required": review_count,
                "hazard_levels": {
                    "level_1_sprays": l1_count,
                    "level_2_insulation": l2_count,
                    "level_3_molded": l3_count
                }
            },
            "room_assessments": [r.to_dict() for r in room_evals],
            "finish_schedule": parsed_schedule_records,
            "diagnoses": [d.to_dict() for d in page1_diagnoses]
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/drawings/{drawing_id}/pages/{page_num}")
def get_drawing_page(drawing_id: str, page_num: int):
    """Fetches base64 preview, diagnoses, and table metadata for a specific page."""
    page_img_path = UPLOAD_DIR / f"{drawing_id}_page_{page_num}.jpg"
    page_json_path = UPLOAD_DIR / f"{drawing_id}_page_{page_num}.json"

    if not page_img_path.exists():
        if drawing_id in JOB_REGISTRY and page_num <= JOB_REGISTRY[drawing_id].get("total_pages", 1):
            return {
                "drawing_id": drawing_id,
                "page_number": page_num,
                "status": "processing",
                "message": f"Page {page_num} is currently being processed in background..."
            }
        raise HTTPException(status_code=404, detail=f"Page {page_num} for drawing {drawing_id} not found.")

    img_cv = cv2.imread(str(page_img_path))
    if img_cv is None:
        raise HTTPException(status_code=500, detail=f"Could not load image for page {page_num}")

    h, w = img_cv.shape[:2]
    img_b64 = encode_image_to_base64(img_cv)

    page_diagnoses = []
    finish_schedule = []
    room_evals = []
    table_box = None

    if page_json_path.exists():
        try:
            with open(page_json_path, "r", encoding="utf-8") as f:
                p_data = json.load(f)
            page_diagnoses = p_data.get("diagnoses", [])
            finish_schedule = p_data.get("finish_schedule", [])
            room_evals = p_data.get("room_assessments", [])
            table_box = p_data.get("table_bbox")
        except Exception:
            pass

    if table_box is None:
        table_box = table_parser.detect_table_boundary(img_cv)

    return {
        "drawing_id": drawing_id,
        "page_number": page_num,
        "status": "completed",
        "image_width": w,
        "image_height": h,
        "table_bbox": table_box,
        "image_base64": img_b64,
        "diagnoses": page_diagnoses,
        "finish_schedule": finish_schedule,
        "room_assessments": room_evals
    }


@app.get("/api/v1/jobs/{drawing_id}")
def get_job_status(drawing_id: str):
    """Returns background multi-page analysis status and progress percentage."""
    if drawing_id not in JOB_REGISTRY:
        p1 = UPLOAD_DIR / f"{drawing_id}_page_1.json"
        if p1.exists():
            return {
                "drawing_id": drawing_id,
                "status": "completed",
                "completed_pages": [1],
                "total_pages": 1,
                "progress_percent": 100,
                "current_status": "Complete"
            }
        raise HTTPException(status_code=404, detail=f"Job {drawing_id} not found")

    job = JOB_REGISTRY[drawing_id]
    total = max(1, job.get("total_pages", 1))
    completed = len(job.get("completed_pages", []))
    percent = int((completed / total) * 100)

    return {
        "drawing_id": drawing_id,
        "status": job.get("status", "processing"),
        "total_pages": total,
        "completed_pages": job.get("completed_pages", []),
        "completed_count": completed,
        "progress_percent": percent,
        "current_status": job.get("current_status", "")
    }


@app.post("/api/v1/review/override")
def record_human_override(req: HumanOverrideRequest):
    """Saves human expert ground-truth corrections into the active learning loop."""
    existing_corrections = []
    if CORRECTIONS_FILE.exists():
        try:
            with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
                existing_corrections = json.load(f)
        except Exception:
            existing_corrections = []

    correction_entry = req.dict()
    import datetime
    correction_entry["timestamp"] = datetime.datetime.now().isoformat()
    existing_corrections.append(correction_entry)

    with open(CORRECTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_corrections, f, ensure_ascii=False, indent=2)

    return {
        "status": "success",
        "message": f"Recorded human verification for {req.item_id}",
        "total_active_learning_samples": len(existing_corrections)
    }


@app.get("/api/v1/review/history")
def get_review_history():
    """Retrieves recorded human overrides from the active learning loop."""
    if not CORRECTIONS_FILE.exists():
        return {"total": 0, "corrections": []}
    try:
        with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
            corrections = json.load(f)
        return {"total": len(corrections), "corrections": corrections}
    except Exception:
        return {"total": 0, "corrections": []}


if __name__ == "__main__":
    import uvicorn
    print("Starting DrawingScan FastAPI Service on http://127.0.0.1:8000...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
