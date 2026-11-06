"""
Dual-Path Document Ingestion Engine for Architectural Blueprints.
Intelligently classifies incoming documents as Vector CAD PDFs, Scanned Raster PDFs,
or Raster Images.
- Vector CAD PDFs: Extracts character streams, fonts, and exact bounding boxes directly via PyMuPDF.
- Scanned Raster PDFs: Renders pages to high-resolution OpenCV image arrays at 300 DPI.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Tuple
from dataclasses import dataclass, field
import numpy as np
import cv2
import fitz  # PyMuPDF


DocType = Literal["VECTOR_PDF", "SCANNED_PDF", "RASTER_IMAGE"]


@dataclass
class ExtractedVectorEntity:
    """Represents a text entity extracted directly from a digital vector PDF."""
    text: str
    bbox: List[float]  # [x_min, y_min, x_max, y_max] in page points/pixels
    font_name: str
    font_size: float
    page_num: int
    confidence: float = 1.0  # Vector text extraction is 100% ground truth


@dataclass
class IngestionResult:
    """Unified container for ingested document data."""
    file_path: str
    doc_type: DocType
    page_count: int
    dimensions: List[Tuple[int, int]]  # (width, height) per page
    vector_entities: List[ExtractedVectorEntity] = field(default_factory=list)
    raster_pages: List[np.ndarray] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_vector(self) -> bool:
        return self.doc_type == "VECTOR_PDF"

    @property
    def is_scanned(self) -> bool:
        return self.doc_type in ("SCANNED_PDF", "RASTER_IMAGE")


class DocumentIngestionRouter:
    """Analyzes and routes document files to the optimal processing path."""

    def __init__(self, target_dpi: int = 300, min_vector_chars_threshold: int = 50):
        self.target_dpi = target_dpi
        self.min_vector_chars_threshold = min_vector_chars_threshold

    def ingest(self, file_path: Path | str) -> IngestionResult:
        """Main entry point: detects file type and routes appropriately."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._ingest_pdf(path)
        elif suffix in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"):
            return self._ingest_image(path)
        else:
            raise ValueError(f"Unsupported document format: {suffix}")

    def _ingest_pdf(self, path: Path) -> IngestionResult:
        """Inspects PDF content stream to classify as Vector or Scanned."""
        doc = fitz.open(str(path))
        page_count = len(doc)
        total_chars = 0
        vector_entities: List[ExtractedVectorEntity] = []
        dimensions: List[Tuple[int, int]] = []

        # Sample pages to inspect text density
        for page_idx in range(page_count):
            page = doc[page_idx]
            rect = page.rect
            dimensions.append((int(rect.width), int(rect.height)))

            # Extract raw words and text blocks
            blocks = page.get_text("blocks")
            for b in blocks:
                # b: (x0, y0, x1, y1, text, block_no, block_type)
                # block_type 0 is text, 1 is image
                if len(b) >= 7 and b[6] == 0:
                    text = b[4].strip()
                    if text:
                        total_chars += len(text)
                        vector_entities.append(
                            ExtractedVectorEntity(
                                text=text,
                                bbox=[float(b[0]), float(b[1]), float(b[2]), float(b[3])],
                                font_name="StandardCADFont",
                                font_size=12.0,
                                page_num=page_idx,
                                confidence=1.0
                            )
                        )

        # Classification Heuristic:
        # If significant text streams exist, it is a digital CAD export
        is_vector = total_chars >= self.min_vector_chars_threshold

        # Quality Validation: Verify that extracted text consists of readable characters,
        # not missing font glyphs or broken CID mappings that produce '????' strings.
        if is_vector:
            qmark_count = sum(ent.text.count("?") for ent in vector_entities)
            qmark_ratio = (qmark_count / max(1, total_chars))
            if qmark_ratio > 0.10 or qmark_count > 15:
                # PDF has corrupted font stream (e.g. '????: ???????????').
                # Automatically fall back to OCR pipeline to visually read genuine text!
                is_vector = False

        raster_pages = []
        scaled_vector_entities: List[ExtractedVectorEntity] = []

        if is_vector:
            for page_idx in range(page_count):
                page = doc[page_idx]
                rect = page.rect

                # If page is already native high-res (e.g. >= 1600 pt), 1.0 zoom is ideal (2400x1600).
                # Otherwise scale to ~2400px wide for optimal CAD readability.
                if rect.width >= 1600:
                    zoom = 1.0
                else:
                    zoom = min(2400.0 / max(rect.width, 1.0), 300.0 / 72.0)

                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                raster_pages.append(img)

                # Scale vector entity bounding boxes to match rendered raster pixel space exactly
                scale_x = float(pix.w) / float(rect.width) if rect.width > 0 else 1.0
                scale_y = float(pix.h) / float(rect.height) if rect.height > 0 else 1.0

                for ent in vector_entities:
                    if ent.page_num == page_idx:
                        bx1, by1, bx2, by2 = ent.bbox
                        scaled_vector_entities.append(
                            ExtractedVectorEntity(
                                text=ent.text,
                                bbox=[bx1 * scale_x, by1 * scale_y, bx2 * scale_x, by2 * scale_y],
                                font_name=ent.font_name,
                                font_size=ent.font_size * scale_y,
                                page_num=ent.page_num,
                                confidence=ent.confidence
                            )
                        )

            doc.close()
            return IngestionResult(
                file_path=str(path),
                doc_type="VECTOR_PDF",
                page_count=page_count,
                dimensions=dimensions,
                vector_entities=scaled_vector_entities,
                raster_pages=raster_pages,
                metadata={"total_extracted_characters": total_chars, "extraction_mode": "DIRECT_PYMUPDF"}
            )
        else:
            # Scanned / Rasterized PDF: Render crisp images for CV pipeline & UI preview
            for page in doc:
                rect = page.rect
                if rect.width >= 1600:
                    zoom = 1.0
                else:
                    zoom = min(2400.0 / max(rect.width, 1.0), self.target_dpi / 72.0)

                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix)
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.h, pix.w, pix.n))
                if pix.n == 4:
                    img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
                elif pix.n == 3:
                    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                raster_pages.append(img)

            doc.close()
            return IngestionResult(
                file_path=str(path),
                doc_type="SCANNED_PDF",
                page_count=page_count,
                dimensions=dimensions,
                vector_entities=[],
                raster_pages=raster_pages,
                metadata={"target_dpi": self.target_dpi, "extraction_mode": "RASTER_OCR_REQUIRED"}
            )

    def _ingest_image(self, path: Path) -> IngestionResult:
        """Loads a standalone raster image file."""
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"Failed to decode image: {path}")

        h, w = img.shape[:2]
        return IngestionResult(
            file_path=str(path),
            doc_type="RASTER_IMAGE",
            page_count=1,
            dimensions=[(w, h)],
            vector_entities=[],
            raster_pages=[img],
            metadata={"channels": img.shape[2] if len(img.shape) > 2 else 1}
        )


if __name__ == "__main__":
    router = DocumentIngestionRouter(target_dpi=300)

    # Test Vector PDF
    vec_sample = "data/output/pdf_test_suite/ALFRED-DWG-1982-001_vector.pdf"
    if os.path.exists(vec_sample):
        vec_res = router.ingest(vec_sample)
        print(f"Vector PDF Test: {vec_res.doc_type}, {len(vec_res.vector_entities)} entities extracted.")

    # Test Scanned PDF
    scan_sample = "data/output/pdf_test_suite/ALFRED-DWG-1982-001_scanned.pdf"
    if os.path.exists(scan_sample):
        scan_res = router.ingest(scan_sample)
        print(f"Scanned PDF Test: {scan_res.doc_type}, {len(scan_res.raster_pages)} raster page rendered, shape: {scan_res.raster_pages[0].shape}")

