import time, cv2, torch
from models.layout.hierarchical_segmenter import HierarchicalROISegmenter
import easyocr

img_path = "data/output/degraded/ALFRED-DWG-1982-001_scanned.jpg"
img = cv2.imread(img_path)
h, w = img.shape[:2]
print(f"Testing image {w}x{h}")

# Segment into ROIs
t0 = time.time()
segmenter = HierarchicalROISegmenter()
rois = segmenter.segment(img)
t_seg = time.time() - t0
print(f"Hierarchical segmentation: {len(rois)} ROIs in {t_seg*1000:.1f}ms")

# Test EasyOCR on GPU
reader = easyocr.Reader(["ja", "en"], gpu=True, verbose=False)

# 1. EasyOCR on full image
t0 = time.time()
res_full = reader.readtext(img)
t_easy_full = time.time() - t0
print(f"EasyOCR Full-Sheet on GPU: {len(res_full)} items in {t_easy_full:.2f}s")

# 2. EasyOCR on ROIs only
t0 = time.time()
roi_items = []
for r in rois:
    res = reader.readtext(r.crop)
    roi_items.extend(res)
t_easy_roi = time.time() - t0
print(f"EasyOCR on {len(rois)} ROIs: {len(roi_items)} items in {t_easy_roi:.2f}s")

# Print detected text samples
print("\nSample detected texts:")
for item in roi_items[:20]:
    t_safe = item[1].encode('ascii', 'backslashreplace').decode('ascii')
    print(f" - {t_safe} (conf: {item[2]:.2f})")

