"""
Master Dataset Generation Script for Stage 1.
Synthesizes a benchmark dataset of Japanese architectural blueprints:
- Digital Vector PDFs (with embedded searchable Japanese text & vector CAD geometry)
- Raster Images & DXF CAD files
- Scanned & Degraded Blueprints (skew, optical blur, photocopy noise)
- Pixel-accurate Ground Truth JSON files (with Asbestos Level 1/2/3 labels)
- Dataset Manifest Index
"""

from __future__ import annotations
import os
import json
from pathlib import Path
from typing import List, Dict, Any
import fitz  # PyMuPDF

from data.database.db_manager import MaterialsDatabase
from data.generator.cad_generator import CADBlueprintGenerator
from data.degradation.scan_effects import ScanDegradationEngine


def generate_benchmark_suite(
    count: int = 5,
    base_output_dir: str = "data/output"
) -> Dict[str, Any]:
    """Generates a complete multi-modal benchmark suite."""
    out_dir = Path(base_output_dir)
    clean_dir = out_dir / "clean"
    deg_dir = out_dir / "degraded"
    pdf_dir = out_dir / "pdf_test_suite"

    clean_dir.mkdir(parents=True, exist_ok=True)
    deg_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)

    db = MaterialsDatabase()
    generator = CADBlueprintGenerator(db=db)
    degrader = ScanDegradationEngine()

    manifest_entries = []

    print(f"=== Starting Generation of {count} Architectural Blueprint Sets ===")

    for i in range(1, count + 1):
        doc_id = f"ALFRED-DWG-1982-{i:03d}"
        seed = 100 + i

        # 1. Generate Clean CAD and Raster PNG + GT
        print(f"[{i}/{count}] Generating clean CAD & raster for {doc_id}...")
        clean_gt = generator.generate(doc_id, clean_dir, seed=seed)
        png_path = clean_dir / f"{doc_id}.png"
        gt_path = clean_dir / f"{doc_id}_gt.json"

        # 2. Generate Digital Vector PDF (Embedded text & vector stream)
        # Using PyMuPDF to embed true selectable text and CAD lines
        vector_pdf_path = pdf_dir / f"{doc_id}_vector.pdf"
        _create_vector_pdf(vector_pdf_path, clean_gt, png_path)

        # 3. Generate Degraded Scanned Image & Scanned PDF
        skew = (-1.0) ** i * (1.2 + (i * 0.4))  # Alternating positive/negative skew
        blur = 3 if i % 2 == 1 else 1
        noise = 0.005 + (i * 0.002)

        deg_img_path = deg_dir / f"{doc_id}_scanned.jpg"
        deg_gt_path = deg_dir / f"{doc_id}_scanned_gt.json"
        deg_pdf_path = pdf_dir / f"{doc_id}_scanned.pdf"

        print(f"[{i}/{count}] Applying scan degradation (skew: {skew:.1f}°, blur: {blur}, noise: {noise:.3f})...")
        deg_gt = degrader.degrade(
            image_path=png_path,
            ground_truth_path=gt_path,
            output_image_path=deg_img_path,
            output_gt_path=deg_gt_path,
            skew_angle=skew,
            blur_ksize=blur,
            noise_density=noise
        )

        # Convert degraded scan to PDF
        _convert_image_to_pdf(deg_img_path, deg_pdf_path)

        manifest_entries.append({
            "drawing_id": doc_id,
            "seed": seed,
            "clean_png": str(png_path.relative_to(out_dir)),
            "clean_dxf": str((clean_dir / f"{doc_id}.dxf").relative_to(out_dir)),
            "vector_pdf": str(vector_pdf_path.relative_to(out_dir)),
            "scanned_jpg": str(deg_img_path.relative_to(out_dir)),
            "scanned_pdf": str(deg_pdf_path.relative_to(out_dir)),
            "total_annotations": clean_gt["annotation_count"],
            "asbestos_positive_count": clean_gt["asbestos_positive_count"],
            "non_asbestos_count": clean_gt["non_asbestos_count"],
            "applied_skew": skew
        })

    # Save Master Manifest
    manifest = {
        "dataset_name": "DrawingScan Synthetic Asbestos Blueprint Benchmark",
        "created_for": "Alfred Company Ltd. R&D AI Engineer Evaluation",
        "total_documents": len(manifest_entries),
        "total_annotations": sum(e["total_annotations"] for e in manifest_entries),
        "total_asbestos_positive_items": sum(e["asbestos_positive_count"] for e in manifest_entries),
        "total_non_asbestos_items": sum(e["non_asbestos_count"] for e in manifest_entries),
        "entries": manifest_entries
    }

    manifest_path = out_dir / "dataset_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n=== Dataset Benchmark Suite Generation Complete ===")
    print(f"Manifest written to: {manifest_path}")
    print(f"Total drawings: {manifest['total_documents']}")
    print(f"Total labeled text items: {manifest['total_annotations']}")
    print(f"Total Asbestos Positive annotations: {manifest['total_asbestos_positive_items']}")
    print(f"Total Non-Asbestos annotations: {manifest['total_non_asbestos_items']}")

    return manifest


def _create_vector_pdf(pdf_path: Path, gt_data: Dict[str, Any], raster_img_path: Path) -> None:
    """Creates a high-resolution PDF with embedded vector text coordinates."""
    doc = fitz.open()
    w, h = gt_data["dimensions"]["width"], gt_data["dimensions"]["height"]
    page = doc.new_page(width=w, height=h)

    # Insert background drawing image
    rect = fitz.Rect(0, 0, w, h)
    page.insert_image(rect, filename=str(raster_img_path))

    # Also insert invisible selectable text stream matching exact bounding boxes
    # This enables testing the Vector Extraction pipeline in Stage 2
    for anno in gt_data["annotations"]:
        bbox = anno["bbox"]
        text = anno["text"]
        # In PyMuPDF, insert_text at (x, baseline_y) produces clean isolated text tokens
        pt = fitz.Point(bbox[0], bbox[3] - 2)
        try:
            page.insert_text(
                pt,
                text,
                fontname="japan",
                fontsize=11,
                render_mode=3  # Invisible text for OCR/searchable PDF testing
            )
        except Exception:
            try:
                page.insert_text(pt, text, fontsize=11, render_mode=3)
            except Exception:
                pass

    doc.save(str(pdf_path))
    doc.close()


def _convert_image_to_pdf(img_path: Path, pdf_path: Path) -> None:
    """Converts a scanned degraded image into a rasterized single-page PDF."""
    doc = fitz.open()
    img_doc = fitz.open(str(img_path))
    pdfbytes = img_doc.convert_to_pdf()
    img_pdf = fitz.open("pdf", pdfbytes)
    page = doc.new_page(width=img_pdf[0].rect.width, height=img_pdf[0].rect.height)
    page.show_pdf_page(page.rect, img_pdf, 0)
    doc.save(str(pdf_path))
    doc.close()
    img_doc.close()


if __name__ == "__main__":
    generate_benchmark_suite(count=5)

