"""
DrawingScan: Interactive Blueprint Asbestos Review & Diagnostics Interface.
Designed for Alfred Company Ltd. (Hamamatsu, Japan).
Features:
1. Color-coded bounding box blueprint visualization (Red = Asbestos, Green = Safe, Yellow = Uncertain)
2. Interactive item inspector displaying raw OCR, NFKC normalized text, and MLIT citations
3. Human-in-the-Loop Active Learning override form
4. Finish Schedule (特記仕上表) structured table viewer
5. One-click CSV diagnostic report export
"""

from __future__ import annotations
import os
import json
from pathlib import Path
import numpy as np
import cv2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

from data.database.db_manager import MaterialsDatabase
from core.preprocess.pipeline import PreprocessingPipeline
from models.layout.table_parser import FinishScheduleTableParser
from nlp.classifier import AsbestosDiagnosticClassifier, DrawingItemDiagnosis


st.set_page_config(
    page_title="DrawingScan | Alfred Asbestos Diagnostics",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card-red { background-color: #ffebee; border-left: 5px solid #d32f2f; padding: 10px 15px; border-radius: 4px; }
    .metric-card-green { background-color: #e8f5e9; border-left: 5px solid #388e3c; padding: 10px 15px; border-radius: 4px; }
    .metric-card-yellow { background-color: #fffde7; border-left: 5px solid #fbc02d; padding: 10px 15px; border-radius: 4px; }
    .metric-card-blue { background-color: #e3f2fd; border-left: 5px solid #1976d2; padding: 10px 15px; border-radius: 4px; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_components():
    """Initializes and caches pipeline singletons."""
    db = MaterialsDatabase()
    classifier = AsbestosDiagnosticClassifier(db=db)
    table_parser = FinishScheduleTableParser()
    return db, classifier, table_parser


db, classifier, table_parser = load_components()

# ==========================================
# SIDEBAR CONTROLS
# ==========================================
st.sidebar.image("https://img.icons8.com/fluency/96/blueprint.png", width=64)
st.sidebar.title("DrawingScan")
st.sidebar.caption("AI-Powered Asbestos Identification in Engineering Drawings")
st.sidebar.markdown("**Alfred Company Ltd. | Hamamatsu R&D**")
st.sidebar.markdown("---")

# Sample Drawing Selector or Upload
input_mode = st.sidebar.radio("Select Input Mode:", ["Benchmark Suite Samples", "Upload Blueprint"])

selected_image_path = None
selected_gt_path = None

if input_mode == "Benchmark Suite Samples":
    samples = {
        "ALFRED-DWG-1982-001 (Degraded Scan 1.6°)": (
            "data/output/degraded/ALFRED-DWG-1982-001_scanned.jpg",
            "data/output/degraded/ALFRED-DWG-1982-001_scanned_gt.json"
        ),
        "ALFRED-DWG-1982-002 (Clean CAD Blueprint)": (
            "data/output/clean/ALFRED-DWG-1982-002.png",
            "data/output/clean/ALFRED-DWG-1982-002_gt.json"
        ),
        "ALFRED-DWG-1982-003 (Degraded Scan 2.4°)": (
            "data/output/degraded/ALFRED-DWG-1982-003_scanned.jpg",
            "data/output/degraded/ALFRED-DWG-1982-003_scanned_gt.json"
        )
    }
    choice = st.sidebar.selectbox("Choose Blueprint:", list(samples.keys()))
    selected_image_path, selected_gt_path = samples[choice]

else:
    uploaded = st.sidebar.file_uploader("Upload drawing (PDF, PNG, JPG):", type=["pdf", "png", "jpg", "jpeg"])
    if uploaded is not None:
        temp_dir = Path("data/uploads")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / uploaded.name
        with open(temp_file, "wb") as f:
            f.write(uploaded.getbuffer())
        selected_image_path = str(temp_file)

# Database Metrics in Sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("MLIT Knowledge Base")
db_stats = db.summary()
st.sidebar.write(f"• **Level 1 (Friable Sprays):** {db_stats['level_1_friable']}")
st.sidebar.write(f"• **Level 2 (Thermal Insulation):** {db_stats['level_2_insulation']}")
st.sidebar.write(f"• **Level 3 (Molded Products):** {db_stats['level_3_molded']}")
st.sidebar.write(f"• **Safe Controls:** {db_stats['non_asbestos_controls']}")
st.sidebar.write(f"• **Indexed Search Keys:** {db_stats['indexed_lookup_keys']}")


# ==========================================
# MAIN APPLICATION INTERFACE
# ==========================================
st.title("🏗️ DrawingScan: Architectural Asbestos Diagnostics")
st.markdown("Automated bilingual extraction, Finish Schedule table parsing, and 4-tier MLIT regulatory cross-matching.")

if selected_image_path and os.path.exists(selected_image_path):
    # Load Image
    img_cv = cv2.imread(selected_image_path)
    if img_cv is None:
        st.error(f"Failed to read image: {selected_image_path}")
        st.stop()

    img_rgb = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
    h, w = img_rgb.shape[:2]

    # Load annotations from GT or run live diagnostic
    with st.spinner("Analyzing document geometry, OCR tokens, and MLIT regulatory status..."):
        if selected_gt_path and os.path.exists(selected_gt_path):
            with open(selected_gt_path, "r", encoding="utf-8") as f:
                gt_data = json.load(f)
            input_items = gt_data["annotations"]
        else:
            # Fallback for uploaded raw image
            table_box = table_parser.detect_table_boundary(img_cv)
            from models.ocr.engine import BilingualOCREngine
            ocr = BilingualOCREngine(gpu=True)
            ocr_preds = ocr.recognize(img_cv)
            input_items = [{"text": p.text, "bbox": p.bbox, "confidence": p.confidence} for p in ocr_preds]

        # Detect table boundary
        table_box = table_parser.detect_table_boundary(img_cv)

        # Run Stage 4 Diagnostics
        diagnoses: List[DrawingItemDiagnosis] = classifier.diagnose_drawing(input_items, table_bbox=table_box)

    # ==========================================
    # 1. TOP METRIC CARDS
    # ==========================================
    col1, col2, col3, col4 = st.columns(4)
    pos_count = sum(1 for d in diagnoses if d.status == "POSITIVE")
    neg_count = sum(1 for d in diagnoses if d.status == "NEGATIVE")
    unc_count = sum(1 for d in diagnoses if d.status == "UNCERTAIN")
    rev_count = sum(1 for d in diagnoses if d.requires_human_review)

    with col1:
        st.markdown(f"""
        <div class="metric-card-blue">
            <h4 style="margin:0; color:#1565c0;">Total Annotations</h4>
            <h2 style="margin:0;">{len(diagnoses)}</h2>
            <small>Filtered dimensions & noise</small>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card-red">
            <h4 style="margin:0; color:#c62828;">🔴 Asbestos Positive</h4>
            <h2 style="margin:0;">{pos_count}</h2>
            <small>Levels 1, 2, and 3 matched</small>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="metric-card-green">
            <h4 style="margin:0; color:#2e7d32;">🟢 Non-Asbestos</h4>
            <h2 style="margin:0;">{neg_count}</h2>
            <small>Certified safe materials</small>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card-yellow">
            <h4 style="margin:0; color:#f57f17;">🟡 Review Required</h4>
            <h2 style="margin:0;">{rev_count}</h2>
            <small>Uncertain or fuzzy matches</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("###")

    # ==========================================
    # 2. DRAW OVERLAYS ON BLUEPRINT
    # ==========================================
    annotated_img = Image.fromarray(img_rgb)
    draw = ImageDraw.Draw(annotated_img)

    try:
        font_box = ImageFont.truetype("C:/Windows/Fonts/msgothic.ttc", 18)
    except Exception:
        font_box = ImageFont.load_default()

    # Draw color-coded bounding boxes
    for idx, d in enumerate(diagnoses):
        bx1, by1, bx2, by2 = d.bbox

        if d.status == "POSITIVE":
            color = (220, 20, 60)   # Red
            fill_color = (255, 235, 238, 70)
        elif d.status == "NEGATIVE":
            color = (34, 139, 34)   # Green
            fill_color = (232, 245, 233, 70)
        else:
            color = (255, 165, 0)   # Orange/Yellow
            fill_color = (255, 249, 196, 70)

        # Draw box and tag
        draw.rectangle([bx1, by1, bx2, by2], outline=color, width=3)
        tag_text = f"#{idx+1}"
        draw.rectangle([bx1, by1 - 22, bx1 + 35, by1], fill=color)
        draw.text((bx1 + 4, by1 - 20), tag_text, fill=(255, 255, 255), font=font_box)

    # Highlight table grid if detected
    if table_box:
        tx1, ty1, tx2, ty2 = table_box
        draw.rectangle([tx1, ty1, tx2, ty2], outline=(30, 144, 255), width=2)
        draw.text((tx1 + 5, ty1 + 5), "仕上表 GRID", fill=(30, 144, 255), font=font_box)

    # ==========================================
    # 3. INTERACTIVE COLUMNS: VIEWER + INSPECTOR
    # ==========================================
    view_col, inspect_col = st.columns([1.5, 1.0])

    with view_col:
        st.subheader("Architectural Drawing Overlay")
        st.image(annotated_img, use_container_width=True)
        st.caption("🔴 Red: Asbestos Contained | 🟢 Green: Safe Material | 🟡 Yellow: Uncertain / Low-Confidence")

    with inspect_col:
        st.subheader("Diagnostic Inspector")

        item_options = [f"#{i+1}: {d.normalized_text[:28]}" for i, d in enumerate(diagnoses)]
        selected_option = st.selectbox("Select Detected Annotation to Inspect:", item_options)
        selected_idx = int(selected_option.split(":")[0].replace("#", "")) - 1
        item: DrawingItemDiagnosis = diagnoses[selected_idx]

        # Inspector Card
        with st.container():
            status_color = "#c62828" if item.status == "POSITIVE" else ("#2e7d32" if item.status == "NEGATIVE" else "#f57f17")
            st.markdown(f"""
            <div style="border: 2px solid {status_color}; padding: 15px; border-radius: 6px; background-color: #fafafa;">
                <h3 style="margin-top:0; color:{status_color};">{item.status} [{item.hazard_level}]</h3>
                <p><strong>Item ID:</strong> <code>{item.item_id}</code></p>
                <p><strong>Raw OCR Text:</strong> <code>{item.raw_text}</code></p>
                <p><strong>Normalized:</strong> {item.normalized_text}</p>
                <p><strong>Matched Material:</strong> {item.matched_material_ja} <em>({item.matched_material_en})</em></p>
                <p><strong>Match Tier:</strong> <code>{item.match_tier}</code> (Confidence: <strong>{item.confidence*100:.1f}%</strong>)</p>
                <p><strong>MLIT Regulatory Note:</strong><br><small>{item.regulatory_citation}</small></p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("###")
        st.subheader("Human-in-the-Loop Override")
        with st.form(key=f"override_form_{item.item_id}"):
            new_status = st.selectbox("Confirm or Override Status:", ["POSITIVE", "NEGATIVE", "UNCERTAIN"], index=["POSITIVE", "NEGATIVE", "UNCERTAIN"].index(item.status))
            new_hazard = st.selectbox("Hazard Level:", ["LEVEL_1", "LEVEL_2", "LEVEL_3", "NON_ASBESTOS", "UNCERTAIN"], index=["LEVEL_1", "LEVEL_2", "LEVEL_3", "NON_ASBESTOS", "UNCERTAIN"].index(item.hazard_level))
            notes = st.text_input("Reviewer Notes (Lab verification details):", placeholder="e.g. Chrysotile confirmed via PLM microscopy")
            submit = st.form_submit_button("💾 Save Human Verification")

            if submit:
                # Save to active learning file
                correction = {
                    "item_id": item.item_id,
                    "raw_text": item.raw_text,
                    "normalized_text": item.normalized_text,
                    "corrected_status": new_status,
                    "corrected_hazard_level": new_hazard,
                    "reviewer_notes": notes
                }
                corr_path = Path("data/active_learning_corrections.json")
                existing = []
                if corr_path.exists():
                    try:
                        with open(corr_path, "r", encoding="utf-8") as f:
                            existing = json.load(f)
                    except Exception:
                        existing = []
                existing.append(correction)
                with open(corr_path, "w", encoding="utf-8") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)

                st.success(f"Verification saved for {item.item_id}! Logged into active learning retraining pool.")

    # ==========================================
    # 4. STRUCTURED SCHEDULE & EXPORT TABLE
    # ==========================================
    st.markdown("---")
    st.subheader("📊 Complete Material Inspection Table")

    table_data = []
    for idx, d in enumerate(diagnoses):
        table_data.append({
            "No.": f"#{idx+1}",
            "Item ID": d.item_id,
            "Raw Text": d.raw_text,
            "Normalized Text": d.normalized_text,
            "Status": d.status,
            "Hazard Level": d.hazard_level,
            "Matched Material (JA)": d.matched_material_ja,
            "Matched Material (EN)": d.matched_material_en,
            "Tier": d.match_tier,
            "Confidence": f"{d.confidence*100:.1f}%",
            "Review Flag": "⚠️ REVIEW" if d.requires_human_review else "✅ OK"
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True)

    # CSV Download
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="📥 Download Diagnostic Report (CSV)",
        data=csv_bytes,
        file_name="asbestos_inspection_report.csv",
        mime="text/csv"
    )

