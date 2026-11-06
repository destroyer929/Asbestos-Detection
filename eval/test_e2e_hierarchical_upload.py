import time, requests, json

url = "http://127.0.0.1:8000/api/v1/analyze"
pdf_path = "testing/REAL-MUNICIPAL-YUKUHASHI-30P.pdf"

print(f"Uploading {pdf_path} (30 Pages) to Hierarchical Multi-Model Pipeline...")
t0 = time.time()
with open(pdf_path, "rb") as f:
    res = requests.post(url, files={"file": ("REAL-MUNICIPAL-YUKUHASHI-30P.pdf", f, "application/pdf")})

t_page1 = time.time() - t0
print(f"Status Code: {res.status_code}")
if res.status_code != 200:
    print("Error:", res.text)
    exit(1)

data = res.json()
drawing_id = data["drawing_id"]
print(f"\n[PAGE 1 FAST-TRACK] Response received in {t_page1:.2f} seconds!")
print(f" - Drawing ID: {drawing_id}")
print(f" - Status: {data.get('status')}")
print(f" - Page Count: {data.get('page_count')}")
print(f" - Current Page: {data.get('current_page')}")
print(f" - Page 1 Material Annotations: {data.get('total_material_annotations')}")
print(f" - Positive Asbestos on Page 1: {data['summary']['asbestos_positive']}")
print(f" - Non-Asbestos Controls on Page 1: {data['summary']['non_asbestos']}")
print(f" - Image Base64 Length: {len(data.get('image_base64', ''))} chars")

# Check Background Progress
print("\nPolling Background Job Status...")
for _ in range(5):
    time.sleep(2)
    j_res = requests.get(f"http://127.0.0.1:8000/api/v1/jobs/{drawing_id}")
    if j_res.status_code == 200:
        j_data = j_res.json()
        print(f" - Status: {j_data['status']} | Completed: {j_data['completed_count']}/{j_data['total_pages']} pages ({j_data['progress_percent']}%) | {j_data['current_status']}")
        if j_data["status"] == "completed":
            break

print("\nHierarchical Multi-Model Pipeline Test Complete!")
