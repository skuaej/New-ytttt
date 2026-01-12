import subprocess
import requests
import json
import os
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Music API")

YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
CACHE_FILE = "cache.json"

# ---------- LOAD CACHE ----------
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r") as f:
            SEARCH_CACHE = json.load(f)
    except Exception:
        SEARCH_CACHE = {}
else:
    SEARCH_CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(SEARCH_CACHE, f, indent=2)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= SEARCH =================
@app.get("/search")
def search(q: str = Query(...)):
    key = q.strip().lower()

    # 1️⃣ Cache hit → instant
    if key in SEARCH_CACHE:
        return {
            "query": q,
            "cached": True,
            "results": SEARCH_CACHE[key]
        }

    # 2️⃣ External search (Piped)
    try:
        r = requests.get(
            "https://piped.video/api/search",
            params={"q": q, "type": "video"},
            timeout=5
        )
        data = r.json()
        items = data.get("items", [])
    except Exception:
        return JSONResponse({"error": "search_failed"}, status_code=500)

    results = []
    for i in items[:10]:
        results.append({
            "title": i.get("title"),
            "url": i.get("url"),
            "duration": i.get("duration"),
            "thumbnail": i.get("thumbnail")
        })

    # 3️⃣ Save to cache
    SEARCH_CACHE[key] = results
    save_cache()

    return {
        "query": q,
        "cached": False,
        "results": results
    }

# ================= AUDIO =================
@app.get("/audio")
def audio(url: str = Query(...)):
    try:
        cmd = [
            YTDLP,
            "--cookies", COOKIES,
            "--force-ipv4",
            "--add-header", "Referer:https://www.youtube.com/",
            "--add-header", "User-Agent:Mozilla/5.0",
            "-f", "bestaudio[ext=m4a]/bestaudio/best",
            "-g",
            url
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        stream = p.stdout.strip()
        if not stream.startswith("http"):
            return JSONResponse({"error": "stream_failed"}, status_code=500)

        return RedirectResponse(stream, status_code=302)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
