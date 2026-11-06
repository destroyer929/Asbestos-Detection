import requests
import json

file_path = r"C:/Users/Karunakar/.gemini/antigravity/brain/186abdf7-aee6-4105-937d-abda97c3689c/.user_uploaded/media_1793911263645_2bba5e9e.jpg"
with open(file_path, "rb") as f:
    r = requests.post("http://127.0.0.1:8000/api/v1/analyze", files={"file": ("drawing.jpg", f, "image/jpeg")})

data = r.json()
with open("eval/verified_diagnoses_all.txt", "w", encoding="utf-8") as out:
    out.write(f"Total: {data['total_material_annotations']}\n")
    out.write(f"Summary: {data['summary']}\n\n")
    for d in data["diagnoses"]:
        line = f"[{d['status']}] [{d['hazard_level']}] {d['matched_material_ja']} ({d['matched_material_en']}) - Raw: '{d['raw_text']}' Conf: {d['confidence']*100:.1f}%\n"
        out.write(line)

