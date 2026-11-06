import time, cv2
from models.ocr.engine import BilingualOCREngine
from models.layout.hierarchical_segmenter import HierarchicalROISegmenter

img_path = "data/output/real_samples/REAL-SAMPLE-01-YUKUHASHI-FINISH-SCHEDULE-1.jpg"
img = cv2.imread(img_path)
if img is None:
    img_path = "data/output/degraded/ALFRED-DWG-1982-001_scanned.jpg"
    img = cv2.imread(img_path)

h, w = img.shape[:2]
print(f"Loaded {img_path} ({w}x{h})")

ocr = BilingualOCREngine(gpu=True)
segmenter = HierarchicalROISegmenter()

# 1. Segment ROIs
t0 = time.time()
rois = segmenter.segment(img)
t_seg = time.time() - t0
print(f"Segmented {len(rois)} ROIs in {t_seg*1000:.1f}ms")

# 2. Recognize each ROI
t0 = time.time()
all_items = []
for idx, r in enumerate(rois):
    t_roi_start = time.time()
    sub_items = ocr.recognize(r.crop)
    t_roi = time.time() - t_roi_start
    print(f" ROI #{idx+1} ({r.category}, {r.width}x{r.height}): {len(sub_items)} items in {t_roi:.2f}s")
    for it in sub_items:
        rx1, ry1 = r.bbox[0], r.bbox[1]
        bx1, by1, bx2, by2 = it.bbox
        it.bbox = [bx1 + rx1, by1 + ry1, bx2 + rx1, by2 + ry1]
        it.polygon = [[p[0] + rx1, p[1] + ry1] for p in it.polygon]
        all_items.append(it)

t_total = time.time() - t0
print(f"\nTotal Hierarchical OCR: {len(all_items)} items in {t_total:.2f}s")

# Check Japanese characters safely
print("First 10 recognized items:")
for it in all_items[:10]:
    t_safe = it.text.encode("ascii", "backslashreplace").decode("ascii")
    print(f" - [{it.confidence:.2f}] {t_safe} at {it.bbox}")
