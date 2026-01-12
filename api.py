import subprocess
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

# ================= ROOT =================
@app.get("/")
def root():
    return {
        "status": "running",
        "endpoints": ["/search?q=", "/audio?url="]
    }

# ================= SEARCH (yt-dlp ONLY) =================
@app.get("/search")
def search(q: str = Query(...)):
    key = q.strip().lower()

    # 1️⃣ CACHE HIT
    if key in SEARCH_CACHE:
        return {
            "query": q,
            "cached": True,
            "results": SEARCH_CACHE[key]
        }

    try:
        # yt-dlp search (ALWAYS WORKS)
        cmd = [
            YTDLP,
            "--skip-download",
            "--print",
            "%(title)s||%(id)s||%(duration)s",
            f"ytsearch10:{q}"
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        lines = p.stdout.strip().split("\n")
        results = []

        for line in lines:
            if "||" not in line:
                continue

            title, vid, duration = line.split("||", 2)
            results.append({
                "title": title,
                "url": f"https://youtu.be/{vid}",
                "duration": int(duration) if duration.isdigit() else None,
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            })

        if not results:
            return JSONResponse({"error": "no_results"}, status_code=404)

        # SAVE CACHE
        SEARCH_CACHE[key] = results
        save_cache()

        return {
            "query": q,
            "cached": False,
            "results": results
        }

    except Exception as e:
        return JSONResponse(
            {"error": "search_failed", "detail": str(e)},
            status_code=500
        )

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
