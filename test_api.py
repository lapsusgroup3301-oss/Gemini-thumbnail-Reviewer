# test_api.py
import requests, pprint

URL = "http://127.0.0.1:8000/api/v1/thumbnail/analyze"
IMAGE_PATH = r"C:\Users\D\Pictures\test_thumbnail.jpg"  # <-- change to a real image path

with open(IMAGE_PATH, "rb") as f:
    files = {"file": (IMAGE_PATH.split("\\")[-1], f, "image/jpeg")}
    data = {"title": "Debug test"}
    r = requests.post(URL, files=files, data=data, timeout=120)
    print("Status:", r.status_code)
    try:
        pprint.pprint(r.json())
    except Exception:
        print(r.text)
