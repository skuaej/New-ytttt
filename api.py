import subprocess
import time
import json
import os
import requests
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
CACHE_FILE = "cache.json"

# ================= CONFIG =================
MAX_CANDIDATES = 5        # try top 5 videos
STREAM_TIMEOUT = 10       # seconds
CACHE_TTL = 24 * 3600     # 24h

# ================= CACHE =================
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r") as f:
            VIDEO_CACHE = json.load(f)
    except Exception:
        VIDEO_CACHE = {}
else:
    VIDEO_CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(VIDEO_CACHE, f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= STREAM FUNCTION =================
def get_stream(video_id: str):
    cmd = [
        YTDLP,
        "--cookies", COOKIES,
        "--force-ipv4",
        "--geo-bypass",
        "--add-header", "Referer:https://www.youtube.com/",
        "--add-header", "User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "-f", "bestaudio[ext=m4a]/bestaudio/best",
        "-g",
        f"https://www.youtube.com/watch?v={video_id}"
    ]

    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=STREAM_TIMEOUT
        )
        stream = p.stdout.strip()
        if stream.startswith("http"):
            return stream
    except Exception:
        pass

    return None

# ================= MAIN ENDPOINT =================
@app.get("/search-audio")
def search_audio(query: str = Query(...)):
    q = query.strip().lower()

    # 1️⃣ If cached → instant
    if q in VIDEO_CACHE:
        stream = get_stream(VIDEO_CACHE[q])
        if stream:
            return RedirectResponse(stream, status_code=302)

    # 2️⃣ FAST external search (Piped)
    try:
        r = requests.get(
            "https://piped.video/api/search",
            params={"q": query, "type": "video"},
            timeout=5
        )
        items = r.json().get("items", [])[:MAX_CANDIDATES]
    except Exception:
        items = []

    # 3️⃣ Try each candidate until one works
    for item in items:
        if "url" not in item:
            continue

        if "v=" not in item["url"]:
            continue

        video_id = item["url"].split("v=")[1]
        stream = get_stream(video_id)

        if stream:
            VIDEO_CACHE[q] = video_id
            save_cache()
            return RedirectResponse(stream, status_code=302)

    return JSONResponse(
        {"error": "no_playable_stream"},
        status_code=500
    )
