"""
Stage 2 Ingestion & Preprocessing Unified Pipeline.
Orchestrates:
1. Ingestion routing (Vector CAD PDF direct extraction vs Scanned Raster conversion)
2. Geometric deskewing and tilt normalization
3. Uneven lighting correction
4. Large-sheet overlapping tiling with tile-to-sheet coordinate mapping
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

from core.ingest.router import DocumentIngestionRouter, IngestionResult
from core.preprocess.geometry import GeometryNormalizer
from core.preprocess.tiler import LargeSheetTiler, ImageTile


class PreprocessingPipeline:
    """End-to-end Stage 2 preprocessing manager."""

    def __init__(
        self,
        target_dpi: int = 300,
        tile_size: int = 1024,
        overlap_ratio: float = 0.20
    ):
        self.router = DocumentIngestionRouter(target_dpi=target_dpi)
        self.normalizer = GeometryNormalizer()
        self.tiler = LargeSheetTiler(tile_size=tile_size, overlap_ratio=overlap_ratio)

    def process(self, file_path: Path | str) -> Dict[str, Any]:
        """
        Executes the full Stage 2 pipeline on a given document.
        Returns processed raster pages, tiles, vector entities (if any), and transformation metadata.
        """
        # 1. Ingest & Route
        ingest_res: IngestionResult = self.router.ingest(file_path)

        page_results = []
        for page_idx, raster_img in enumerate(ingest_res.raster_pages):
            # 2. Deskew & Normalize Illumination
            normalized_img, geom_meta = self.normalizer.process(raster_img)

            # 3. Slice into overlapping tiles
            tiles: List[ImageTile] = self.tiler.tile_image(normalized_img)

            page_results.append({
                "page_num": page_idx,
                "original_shape": raster_img.shape,
                "normalized_shape": normalized_img.shape,
                "detected_skew_angle": geom_meta["detected_skew_angle"],
                "deskew_applied": geom_meta["deskew_applied"],
                "tile_count": len(tiles),
                "tiles": tiles,
                "normalized_image": normalized_img,
                "display_image": geom_meta.get("display_image", raster_img)
            })

        return {
            "file_path": str(file_path),
            "doc_type": ingest_res.doc_type,
            "is_vector": ingest_res.is_vector,
            "vector_entities": ingest_res.vector_entities,
            "total_vector_count": len(ingest_res.vector_entities),
            "page_results": page_results
        }


if __name__ == "__main__":
    pipeline = PreprocessingPipeline(target_dpi=300)

    # 1. Test Scanned Drawing
    scanned_file = "data/output/pdf_test_suite/ALFRED-DWG-1982-001_scanned.pdf"
    res = pipeline.process(scanned_file)
    print(f"Processed: {res['file_path']}")
    print(f"Doc Type: {res['doc_type']}, Vector: {res['is_vector']}")
    p0 = res["page_results"][0]
    print(f"Page 0: {p0['original_shape']} -> Skew detected: {p0['detected_skew_angle']:.2f}°, Tiles generated: {p0['tile_count']}")

    # 2. Test Vector Drawing
    vec_file = "data/output/pdf_test_suite/ALFRED-DWG-1982-001_vector.pdf"
    res_vec = pipeline.process(vec_file)
    print(f"\nProcessed: {res_vec['file_path']}")
    print(f"Doc Type: {res_vec['doc_type']}, Vector entities: {res_vec['total_vector_count']}")

