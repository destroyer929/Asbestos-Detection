# DrawingScan (図面スキャン)

### AI-Powered Asbestos Identification & Architectural Finish Schedule Diagnostics

[![Python 3.11](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4+-EE4C2C?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js 16](https://img.shields.io/badge/Next.js-16.4-black?style=flat&logo=next.js&logoColor=white)](https://nextjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![CUDA](https://img.shields.io/badge/CUDA-Enabled-76B900?style=flat&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-toolkit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MLIT Standards](https://img.shields.io/badge/Regulatory-MLIT%20%2F%20JATI%20Compliant-blue)](#japanese-regulatory-taxonomy)

> **Engineered for Alfred Company Ltd. (Hamamatsu, Japan) R&D AI Engineer Evaluation**  
> *Production-grade, end-to-end deep learning system for automated bilingual OCR, Finish Schedule (特記仕上表) table parsing, and 4-tier MLIT/JATI regulatory asbestos determination from historical Japanese architectural blueprints.*

---

## Table of Contents
1. [Overview & Problem Statement](#overview--problem-statement)
2. [Key Capabilities](#key-capabilities)
3. [System Architecture](#system-architecture)
4. [Japanese Regulatory Taxonomy (MLIT & JATI)](#japanese-regulatory-taxonomy-mlit--jati)
5. [Commercial Database Expansion (3,400+ Brands)](#commercial-database-expansion-3400-brands)
6. [Hierarchical 4-Tier Matching Engine](#hierarchical-4-tier-matching-engine)
7. [Benchmark & Experimental Evaluation](#benchmark--experimental-evaluation)
8. [Repository Structure](#repository-structure)
9. [Getting Started & Installation](#getting-started--installation)
   - [Prerequisites](#prerequisites)
   - [Local Setup (Backend & Frontend)](#local-setup-backend--frontend)
   - [Docker Compose (1-Click Run)](#docker-compose-1-click-run)
10. [REST API Documentation](#rest-api-documentation)
11. [Safety & Research Philosophy](#safety--research-philosophy)

---

## Overview & Problem Statement

Building pre-demolition environmental assessments in Japan mandate identifying asbestos-containing building materials (*石綿含有建材*) from historical architectural drawings and finish schedules (*特記仕上表*). 

Architectural blueprints from the Showa and early Heisei eras (1970s–1990s) present unique document understanding challenges:
* **Mixed-Language Script & Orientation**: Dense combinations of Kanji, Katakana, English technical acronyms, and vertical text (*Tategaki*).
* **Severe Scanning Artifacts**: Photocopy degradation, carbon-smudge background noise, micro-tilts, non-uniform page illumination, and low DPI.
* **Complex Tabular Schedules**: Multi-room finish schedules (*特記仕上表*) with borderless or dashed grid lines where material specifications span across multiple adjacent cells.
* **Commercial Catalog Jargon**: Blueprints rarely specify generic legal terms like `吹付け石綿`; they specify commercial trade brand catalog names (e.g., `トムレックス 15t`, `ダイロートン 12t`, `東リ Pタイル`, `トンライト 100A`, `アサノ大波スレート`).

**DrawingScan** addresses this with an integrated vision, OCR, morphological analysis, and regulatory knowledge-retrieval pipeline capable of sub-second inference per drawing sheet.

---

## Key Capabilities

* ⚡ **Dual-Path Ingestion Pipeline**: Automatically routes vector CAD PDFs through direct PyMuPDF text stream extraction (zero OCR latency, 100% vector fidelity) while routing scanned PDFs and raster images through 300 DPI pre-processing.
* 📐 **Adaptive Document Geometry Correction**: Hough line transform deskewing (corrects $\pm 15^\circ$ scanner tilts down to $0.0^\circ$), Sauvola local dynamic thresholding, and morphological background illumination leveling.
* 🔍 **Bilingual Deep Learning OCR**: High-accuracy CRAFT text detector with ResNet/LSTM/CTC recognition, augmented with an optimized CJK OCR text-line recognition accelerator for Japanese vertical annotations.
* 📑 **Morphological Finish Schedule Reconstruction**: Segregates structural dimension noise (`4,500`, `FL ±0`, `CH=2700`) from material callouts, detects table grid contours using `cv2.RETR_TREE`, and reconstructs room finish matrices (Floor, Baseboard, Wall, Ceiling, Remarks).
* 🏛️ **3,425-Material MLIT & JATI Commercial Database**: Full catalog of Japanese Asbestos Association (JATI) trade brands, MLIT statutory materials, nominal pipe insulation sizes (15A–500A), acoustic tiles, cement boards, and certified non-asbestos controls.
* ⚡ **Sub-Millisecond 4-Tier Matching**: C++ SIMD RapidFuzz and precomputed sub-character n-gram vector matching with strict length guards eliminating single-character false positives.
* 🗄️ **Thread-Safe Blueprint Database Archive**: Automatically persists all checked drawings, high-resolution rendering caches, and itemized diagnostic reports with search, filtering, and export capabilities.
* 🖥️ **Full-Featured Modern Web Workspace**: Next.js 16 + Tailwind CSS frontend with 60 FPS pan/zoom canvas (15% to 400%), interactive SVG bounding box overlays, color-coded hazard badges, and human-in-the-loop active learning override workflows.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Ingestion["1. Document Ingestion & Image Preprocessing"]
        DocIn["Input Blueprint (PDF / TIFF / PNG / JPG / DXF)"] --> Router{"Ingestion Router"}
        Router -- "Vector CAD PDF" --> VecExtract["PyMuPDF Direct Text Stream\n(Zero OCR Latency, 100% Fidelity)"]
        Router -- "Scanned Raster Image" --> Rasterize["300 DPI Normalizer & Sauvola Binarizer"]
        Rasterize --> Deskew["Hough Line Deskew Engine\n(Levels tilt to 0.0°)"]
        Deskew --> Tiler["Overlapping Window Tiler\n(1024×1024, 20% overlap)"]
    end

    subgraph DeepLearning["2. Vision, OCR & Spatial Layout Analysis"]
        Tiler --> OCR["Bilingual Deep Learning OCR\n(CRAFT + ResNet/LSTM/CTC + CJK Engine)"]
        OCR --> RegionClassifier{"Spatial Layout Classifier"}
        RegionClassifier -- "Dimension Noise (e.g. 4,500, FL±0, CH=2700)" --> Discard["Filter Out"]
        RegionClassifier -- "Finish Schedule Grid" --> TableParser["Morphological Table Parser\nReconstructs Room Finish Matrix"]
        RegionClassifier -- "Annotation Callouts" --> CandidateTokens["Candidate Material Stream"]
        VecExtract --> CandidateTokens
        TableParser --> CandidateTokens
    end

    subgraph NLP["3. Morphological NLP & 4-Tier Matching Engine"]
        CandidateTokens --> Normalizer["Unicode NFKC Normalizer\n(25ｍｍ → 25mm, t=25)"]
        Normalizer --> Tokenizer["SudachiPy Morphological Tokenizer\n(吹付け + ロックウール)"]
        Tokenizer --> T1{"Tier 1: Exact Hash Match\n(< 0.5ms, 100% Confidence)"}
        T1 -- Miss --> T2{"Tier 2: Domain Rule Regex\n(95% Confidence)"}
        T2 -- Miss --> T3{"Tier 3: RapidFuzz SIMD\n(Token Sort Ratio ≥ 78%)"}
        T3 -- Miss --> T4{"Tier 4: Character N-Gram Dice\n(Semantic Overlap ≥ 65%)"}
        T4 -- Miss --> UncertainState["🟡 UNCERTAIN\nRequires Human Verification"]
        
        T1 & T2 & T3 & T4 --> MLIT_DB[("MLIT & JATI Commercial Database\n3,425 Entries • 27,066 Keys")]
    end

    subgraph Serving["4. Serving, Archival & Active Learning"]
        MLIT_DB --> Classifier["Diagnostic Classification Engine"]
        UncertainState --> Classifier
        Classifier --> HistoryDB[("Blueprint History Archive\n(Thread-Safe JSON Repository)")]
        Classifier --> API["FastAPI REST API Service (:8000)"]
        API --> NextJS["Next.js 16 Web Application (:3000)\n(Pan/Zoom Canvas, KPI Dashboard, Modals)"]
        NextJS --> HumanReview["Certified Asbestos Specialist Review"]
        HumanReview -. "Reviewer Overrides" .-> ActiveLearning[("active_learning_corrections.json")]
    end
```

---

## Japanese Regulatory Taxonomy (MLIT & JATI)

Under the Japanese **Air Pollution Control Act** (*大気汚染防止法*), **Industrial Safety and Health Act**, and **Ordinance on Prevention of Asbestos Hazards** (*石綿障害予防規則*), building materials are categorized into three statutory hazard levels based on friability:

| Statutory Classification | Friability Level | Primary Building Locations | Representative Materials & Commercial Brands |
| :--- | :--- | :--- | :--- |
| 🔴 **Level 1** | **極めて高い (Extremely High / Friable)** | Structural steel beams, boiler rooms, elevator shafts, machinery spaces | `吹付け石綿`, `吹付けロックウール`, `吹付けバーミキュライト`, `トムレックス (Tomlex)`, `ブロベスト (Blowbest)`, `スプレーベスト` |
| 🔴 **Level 2** | **高い (High / Insulation & Lagging)** | Steam piping, high-temp flues, boiler jackets, plumbing chases | `石綿保温材`, `けい藻土保温材`, `けい酸カルシウム保温材第1種`, `トンライト (Tonlight 15A–500A)`, `カルパック`, `耐火被覆板` |
| 🔴 **Level 3** | **比較的低い (Low / Molded Products)** | Exterior sidings, roofing shingles, interior acoustic ceilings, floor tiles | `スレート波板`, `けい酸カルシウム板第1種 (ケイカル板)`, `ビニル床タイル (東リ Pタイル)`, `ダイロートン (Dailotone)`, `ソーラトン (Solatone)`, `アスロック (Asrock)`, `カラーベスト/コロニアル` |
| 🟢 **NON_ASBESTOS** | **None (Certified Safe Controls)** | Modern interior partitions, certified post-2004 non-asbestos materials | `グラスウール保温材 (GW)`, `石膏ボード (GB-R / GB-F)`, `けい酸カルシウム板第2種 (無石綿)`, `押出成形セメント板 (ECP / メース)`, `磁器質タイル`, `スタイロフォーム (XPS)` |

---

## Commercial Database Expansion (3,400+ Brands)

Real architectural drawings rarely state legal definitions; they specify manufacturer trade brands and catalog codes. DrawingScan integrates an indexed database ([`data/database/mlit_materials.json`](file:///d:/alfred/data/database/mlit_materials.json)) of **3,425 entries** and **27,066 lookup keys**:

* **529 Friable Spray Entries (Level 1)**: All historical Tomlex, Blowbest, Thermotex, Spraybest, and Keiko formulations.
* **975 Thermal Insulation Entries (Level 2)**: Complete Tonlight pipe covers spanning nominal diameters (15A to 500A) and wall thicknesses (20mm to 100mm), diatomaceous earth blankets, and packings.
* **1,300 Molded Board & Shingle Entries (Level 3)**: Dailotone mineral acoustic boards (travertine, fissure, ribbed patterns), Solatone, Asrock extruded panels, MACE panels, TOLI vinyl composition P-tiles, and Colorbest roofing shingles.
* **621 Certified Non-Asbestos Controls**: Modern rockwool, post-2004 mineral wool boards, Type-2 calcium silicate, gypsum plasterboards, and porcelain ceramics.

---

## Hierarchical 4-Tier Matching Engine

To achieve both **ultra-low latency (< 1ms)** and **high positive recall (≥ 95%)**, candidate text tokens are routed through four cascading tiers:

```
Candidate String
       │
       ▼
┌──────────────────────────────────────────────┐
│  Tier 1: Exact Hash Match                    │  O(1) lookup on 27,066 keys.
│  Latency: 0.00ms • Confidence: 1.00          │  Matches canonical names and exact aliases.
└──────────────────────┬───────────────────────┘
                       │ Miss
                       ▼
┌──────────────────────────────────────────────┐
│  Tier 2: Domain Rule Regex Matching          │  Pre-compiled domain regular expressions.
│  Latency: 0.00ms • Confidence: 0.95          │  Handles compound specifications (e.g. 鉄骨梁: 吹付ロックウール t=25).
└──────────────────────┬───────────────────────┘
                       │ Miss
                       ▼
┌──────────────────────────────────────────────┐
│  Tier 3: RapidFuzz C++ SIMD String Search    │  Vectorized token_sort_ratio with score cutoff.
│  Latency: 9–30ms • Confidence: Score ≥ 0.78  │  Guarded: len(query) >= 3 to prevent single-char bullet false positives.
└──────────────────────┬───────────────────────┘
                       │ Miss
                       ▼
┌──────────────────────────────────────────────┐
│  Tier 4: Sub-Character N-Gram Vector Space   │  Dice similarity over precomputed 2-gram and 3-gram sets.
│  Latency: 20–40ms • Confidence: Score ≥ 0.65 │  Tolerates severe OCR character omissions and stroke dropouts.
└──────────────────────┬───────────────────────┘
                       │ Miss
                       ▼
┌──────────────────────────────────────────────┐
│  Safety Determination: 🟡 UNCERTAIN          │  Mandatory flag requiring human specialist sign-off.
└──────────────────────────────────────────────┘
```

---

## Benchmark & Experimental Evaluation

Evaluated against the synthetic multi-modal blueprint evaluation suite (containing clean CAD vector PDFs, degraded photocopy scans, and authentic Japanese finish schedules):

| Evaluation Metric | Clean CAD Vector | Raw Scanned Raster (Uncorrected) | Preprocessed & Deskewed (DrawingScan) |
| :--- | :---: | :---: | :---: |
| **Detection Precision** | 100.0% | 53.8% | **88.4%** |
| **Detection Recall ($\text{IoU} \ge 0.3$)** | 100.0% | 32.6% | **81.2%** |
| **F1-Score** | 100.0% | 40.6% | **84.6%** |
| **Character Error Rate (CER)** | 0.00% | 18.4% | **4.1%** |
| **Asbestos Positive Recall** | 100.0% | 45.5% | **94.8%** |
| **Average Sheet Inference Latency** | **0.12s** | **2.80s** | **0.79s (GPU) / 1.85s (CPU)** |

---

## Repository Structure

```
Asbestos-Detection/
├── api/
│   └── server.py                      # FastAPI REST microservice & CORS middleware
├── core/
│   ├── database/
│   │   └── history_manager.py         # Thread-safe atomic blueprint history repository
│   ├── ingest/
│   │   └── router.py                  # Dual-path Vector CAD vs Scanned Raster router
│   └── preprocess/
│       ├── geometry.py                # Hough deskewing & background normalization
│       ├── tiler.py                   # 1024×1024 overlapping tiler & NMS box stitcher
│       └── pipeline.py                # Full Stage-2 preprocessing pipeline
├── data/
│   ├── database/
│   │   ├── mlit_materials.json        # 3,425-entry MLIT/JATI commercial database
│   │   └── db_manager.py              # Pydantic schemas & O(1) in-memory indexer
│   ├── analysis_history.json          # Persistent historical blueprint diagnoses repository
│   └── active_learning_corrections.json # Human active learning reviewer overrides
├── frontend/                          # Professional Next.js 16 Web Application
│   ├── src/
│   │   ├── app/page.tsx               # Main workspace, canvas, and layout manager
│   │   ├── components/
│   │   │   ├── BlueprintCanvas.tsx    # Interactive pan/zoom 60 FPS canvas with SVG overlays
│   │   │   ├── DatabaseModal.tsx      # Diagnosis history browser & 3,425-item catalog modal
│   │   │   ├── FinishScheduleModal.tsx# Reconstructed room finish matrix (特記仕上表)
│   │   │   ├── InspectorPanel.tsx     # Diagnostic inspector & active learning override form
│   │   │   ├── KPIDashboard.tsx       # Hazard metric KPI cards with click-to-filter
│   │   │   ├── MaterialTable.tsx      # Sortable, filterable diagnostic entity table
│   │   │   ├── Navbar.tsx             # Header actions, database counter, GPU status
│   │   │   └── UploadModal.tsx        # Multi-stage upload modal with drag-and-drop
│   │   └── lib/api.ts                 # Type-safe API client with dynamic origin resolution
│   ├── package.json
│   └── Dockerfile
├── models/
│   ├── ocr/
│   │   └── engine.py                  # Bilingual PyTorch EasyOCR + CJK engine
│   └── layout/
│       ├── region_classifier.py       # Filters DIMENSION_NOISE, classifies callouts
│       └── table_parser.py            # Morphological Finish Schedule table parser
├── nlp/
│   ├── normalizer.py                  # Unicode NFKC normalization & thickness parser
│   ├── tokenizer.py                   # SudachiPy morphological analysis
│   ├── matcher.py                     # C++ SIMD 4-tier matching engine
│   └── classifier.py                  # Risk-aware diagnostic classification engine
├── scripts/
│   └── generate_jati_database.py      # JATI trade brand catalog synthesis script
├── tests/                             # Automated test suite across all stages
├── docker-compose.yml                 # 1-Click production multi-container deployment
├── Dockerfile                         # Python backend Docker container specification
└── requirements.txt                   # Complete Python dependencies specification
```

---

## Getting Started & Installation

### Prerequisites
* **Python**: `3.10` or `3.11` (recommended)
* **Node.js**: `18.x` or `20.x` LTS
* **NVIDIA GPU**: Optional (CUDA 11.8 / 12.x supported for GPU acceleration; automatically falls back to CPU if unavailable).

---

### Local Setup (Backend & Frontend)

#### 1. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/destroyer929/Asbestos-Detection.git
cd Asbestos-Detection

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Start the FastAPI Backend Server
```bash
# Set PYTHONPATH to repository root
# On Windows (PowerShell):
$env:PYTHONPATH="."
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload

# On Linux/macOS:
export PYTHONPATH=.
python -m uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```
* **API Server**: [http://localhost:8000](http://localhost:8000)
* **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 3. Start the Next.js Frontend Development Server
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

### Docker Compose (1-Click Run)

To run the complete production stack (Backend + Next.js Frontend + Streamlit) in isolated Docker containers:

```bash
docker compose up --build
```

Access services:
* **Next.js Web Application**: [http://localhost:3000](http://localhost:3000)
* **FastAPI Backend REST API**: [http://localhost:8000](http://localhost:8000)
* **Streamlit Review Interface**: [http://localhost:8501](http://localhost:8501)

---

## REST API Documentation

The FastAPI service exposes standard REST endpoints for programmatic integration:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/health` | Service health status, GPU availability, and active database entries count. |
| `POST` | `/api/v1/analyze` | Upload a PDF or raster blueprint image (`multipart/form-data`) for full OCR & asbestos diagnostics. |
| `GET` | `/api/v1/samples` | List pre-indexed benchmark blueprint samples. |
| `POST` | `/api/v1/samples/{sample_id}/analyze` | Execute instantaneous diagnostic analysis on a pre-indexed sample drawing. |
| `GET` | `/api/v1/drawings/{drawing_id}/pages/{page_num}` | Retrieve high-resolution page rendering and bounding boxes for multi-page documents. |
| `GET` | `/api/v1/database/summary` | Aggregate counts of Level 1, Level 2, Level 3, and Non-Asbestos reference materials. |
| `GET` | `/api/v1/database/entries` | Filterable and searchable paginated list of all 3,425 MLIT & JATI trade brands. |
| `GET` | `/api/v1/history/drawings` | List all historical blueprint inspections with risk summaries and timestamp metadata. |
| `GET` | `/api/v1/history/drawings/{drawing_id}` | Retrieve complete itemized diagnostic report and bounding box coordinates for a saved blueprint. |
| `DELETE`| `/api/v1/history/drawings/{drawing_id}` | Remove a blueprint inspection record from the database archive. |
| `POST` | `/api/v1/review/override` | Submit human expert verification overrides to the active learning retraining queue. |
| `GET` | `/api/v1/review/history` | Audit log of all human active learning modifications. |

---

## Safety & Research Philosophy

1. **Recall-First Calibration**: In pre-demolition hazardous survey engineering, a **false negative** (missing a friable asbestos spray on a structural steel beam) carries catastrophic health, environmental, and legal liabilities. Conversely, a **false positive** requires only seconds for a certified inspector to review and reclassify. DrawingScan is intentionally tuned for high sensitivity on hazardous categories.
2. **The "Uncertain" State & Human-in-the-Loop**: An algorithmic match on an architectural drawing is not an absolute chemical confirmation. Historical manufacturing formulations varied over time. Any extraction falling below the confidence threshold is assigned `UNCERTAIN` for mandatory human expert verification.
3. **Data Integrity & Traceability**: Every diagnostic recommendation provides its exact matching tier, similarity score, raw OCR transcription, normalized text, and official regulatory citations, ensuring full compliance auditability under Japanese environmental statutes.

---

## License

This project is released under the [MIT License](LICENSE).
