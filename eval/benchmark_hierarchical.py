import time, os, cv2, torch
os.environ["FLAGS_use_mkldnn"] = "0"
from models.ocr.engine import BilingualOCREngine
from models.layout.table_parser import FinishScheduleTableParser

img_path = "testing/REAL-SAMPLE-01-YUKUHASHI-FINISH-SCHEDULE-1.jpg"
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f"Loaded image: {w}x{h}")

ocr = BilingualOCREngine(gpu=True)
parser = FinishScheduleTableParser()

# 1. Baseline Full-Sheet OCR
t0 = time.time()
full_items = ocr.recognize(img)
t_full = time.time() - t0
print(f"[Baseline Full-Sheet OCR] Time: {t_full:.2f}s | Items detected: {len(full_items)}")

# 2. Hierarchical: Detect ROI first, then OCR
t0 = time.time()
t_box = parser.detect_table_boundary(img)
if t_box:
    x1, y1, x2, y2 = t_box
    crop = img[y1:y2, x1:x2]
    crop_items = ocr.recognize(crop)
    t_crop = time.time() - t0
    print(f"[Hierarchical ROI OCR] Time: {t_crop:.2f}s | Table crop: {x2-x1}x{y2-y1} | Items detected: {len(crop_items)}")
    print(f"Speedup: {t_full / max(0.01, t_crop):.2f}x faster!")
else:
    print("Table bbox not detected directly by parser")
