import os
import re
import json
import hashlib
import requests
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================
# CONFIG
# ============================

BASE_DIR = Path(r"C:\Users\andrew\PROJECTS\GitHub\get_xmltvlisting\assets\olympics\milano-cortina-2026")
BASE_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_PATH = BASE_DIR / "manifest.json"
LOG_PATH = BASE_DIR / "download_log.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

WINTER_SPORTS = [
    "biathlon",
    "alpine-skiing",
    "curling",
    "ice-hockey",
    "figure-skating",
    "short-track-speed-skating",
    "skeleton",
    "luge",
    "cross-country-skiing",
    "ski-jumping",
    "freestyle-skiing",
    "snowboard",
    "nordic-combined",
    "ski-mountaineering",
]

SPORT_API = [
    f"https://api.olympics.com/en/content/v1/sports/{slug}"
    for slug in WINTER_SPORTS
]

BRAND_API = [
    "https://api.olympics.com/en/content/v1/olympic-games/milano-cortina-2026",
    "https://api.olympics.com/en/content/v1/olympic-games/milano-cortina-2026/brand",
    "https://api.olympics.com/en/content/v1/olympic-games/milano-cortina-2026/look-of-the-games",
    "https://api.olympics.com/en/content/v1/olympic-games/milano-cortina-2026/mascots",
    "https://api.olympics.com/en/content/v1/olympic-games/milano-cortina-2026/medals",
]

API_ENDPOINTS = SPORT_API + BRAND_API

IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"]

# ============================
# HELPERS
# ============================

def log(msg: str):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def is_image_url(url: str) -> bool:
    lower = url.lower()
    return any(lower.endswith(ext) for ext in IMAGE_EXTS)

def extract_cdn_urls_from_json(data):
    text = json.dumps(data)
    matches = re.findall(r'https?://[^\s"\'()]+', text)
    urls = set()
    for m in matches:
        if is_image_url(m):
            urls.add(m)
    return urls

def download_asset(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        log(f"[ERR] {url} ({e})")
        return None

    parsed = urlparse(url)
    filename = os.path.basename(parsed.path)
    if not filename:
        filename = "asset.bin"

    out_path = BASE_DIR / filename

    with open(out_path, "wb") as f:
        f.write(resp.content)

    digest = sha256_bytes(resp.content)

    log(f"[OK] {url} -> {out_path}")

    return {
        "url": url,
        "filename": filename,
        "sha256": digest,
        "path": str(out_path),
    }

# ============================
# MAIN
# ============================

def main():
    log("=== Milano–Cortina 2026 Asset Harvester (API ONLY) Started ===")

    all_urls = set()

    for endpoint in API_ENDPOINTS:
        log(f"[API] {endpoint}")
        try:
            resp = requests.get(endpoint, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            data = resp.json()
            urls = extract_cdn_urls_from_json(data)
            log(f"  -> found {len(urls)} assets")
            all_urls.update(urls)
        except Exception as e:
            log(f"[ERR] Failed to fetch API {endpoint}: {e}")

    log(f"Total unique assets discovered: {len(all_urls)}")

    manifest = []

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(download_asset, url) for url in sorted(all_urls)]
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                manifest.append(result)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    log(f"Saved manifest: {MANIFEST_PATH}")
    log("=== Completed ===")

if __name__ == "__main__":
    main()
