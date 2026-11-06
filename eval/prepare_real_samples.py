import fitz
from pathlib import Path
import shutil

src_dir = Path("data/real_blueprints")
dest_dir = Path("data/output/real_samples")
dest_dir.mkdir(parents=True, exist_ok=True)

# 1. Full 79P Yukuhashi
src_yukuhashi = src_dir / "Yukuhashi_3965.pdf"
if src_yukuhashi.exists():
    shutil.copyfile(src_yukuhashi, dest_dir / "REAL-MUNICIPAL-YUKUHASHI-79P.pdf")
    print("Copied REAL-MUNICIPAL-YUKUHASHI-79P.pdf")

    # 2. Extract 30P Package (Pages 1 to 30)
    doc_y = fitz.open(str(src_yukuhashi))
    doc_30 = fitz.open()
    for p in range(min(30, len(doc_y))):
        doc_30.insert_pdf(doc_y, from_page=p, to_page=p)
    doc_30.save(str(dest_dir / "REAL-MUNICIPAL-YUKUHASHI-30P.pdf"))
    print(f"Created REAL-MUNICIPAL-YUKUHASHI-30P.pdf with {len(doc_30)} distinct pages")

    # Extract high-res sample images (DPI=200 for crisp text reading)
    # Page 9: Finish Schedule 1
    pix9 = doc_y[8].get_pixmap(dpi=200)
    pix9.save(str(dest_dir / "REAL-SAMPLE-01-YUKUHASHI-FINISH-SCHEDULE-1.jpg"))
    # Page 10: Finish Schedule 2
    pix10 = doc_y[9].get_pixmap(dpi=200)
    pix10.save(str(dest_dir / "REAL-SAMPLE-02-YUKUHASHI-FINISH-SCHEDULE-2.jpg"))
    # Page 11: Floor Plan 1F-2F
    pix11 = doc_y[10].get_pixmap(dpi=200)
    pix11.save(str(dest_dir / "REAL-SAMPLE-03-YUKUHASHI-FLOOR-PLAN-1F-2F.jpg"))
    print("Saved Yukuhashi sample images")

# 3. Saitama Set A (63P)
src_s1 = src_dir / "Saitama_403886.pdf"
if src_s1.exists():
    shutil.copyfile(src_s1, dest_dir / "REAL-SAITAMA-PREFECTURAL-SET-A-63P.pdf")
    print("Copied REAL-SAITAMA-PREFECTURAL-SET-A-63P.pdf")
    doc_s1 = fitz.open(str(src_s1))
    pix_s1 = doc_s1[1].get_pixmap(dpi=150)
    pix_s1.save(str(dest_dir / "REAL-SAMPLE-04-SAITAMA-SCANNED-BLUEPRINT.jpg"))

# 4. Saitama Set B (56P)
src_s2 = src_dir / "Saitama_403883.pdf"
if src_s2.exists():
    shutil.copyfile(src_s2, dest_dir / "REAL-SAITAMA-PREFECTURAL-SET-B-56P.pdf")
    print("Copied REAL-SAITAMA-PREFECTURAL-SET-B-56P.pdf")

# 5. Atsugi (5P Scanned)
src_a = src_dir / "ATSUGI-KIZONN-PUBLIC-FACILITY-5P.pdf"
if src_a.exists():
    shutil.copyfile(src_a, dest_dir / "REAL-ATSUGI-PUBLIC-FACILITY-5P.pdf")
    print("Copied REAL-ATSUGI-PUBLIC-FACILITY-5P.pdf")
    doc_a = fitz.open(str(src_a))
    pix_a = doc_a[0].get_pixmap(dpi=200)
    pix_a.save(str(dest_dir / "REAL-SAMPLE-05-ATSUGI-SCANNED-FLOOR-PLAN.jpg"))

# 6. Nagareyama (3P Finish Schedule)
src_n = src_dir / "NAGAREYAMA-ISYOU-SCHEDULE-AND-PLANS-3P.pdf"
if src_n.exists():
    shutil.copyfile(src_n, dest_dir / "REAL-NAGAREYAMA-SCHEDULE-PLANS-3P.pdf")
    print("Copied REAL-NAGAREYAMA-SCHEDULE-PLANS-3P.pdf")

print("All real blueprints organized successfully!")

