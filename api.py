import subprocess
import json
import os
import requests
import time

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Music API (Fast + Spotify-style)")

# ================= CONFIG =================
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
CACHE_FILE = "cache.json"

AUDIO_CACHE = {}                 # { yt_url: { "stream": url, "ts": time } }
AUDIO_CACHE_TTL = 1800           # 30 min

MIX_CACHE = {"data": None, "ts": 0}
MIX_TTL = 1800                   # 30 min

# ================= SEARCH CACHE =================
if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE, "r") as f:
            SEARCH_CACHE = json.load(f)
        if not isinstance(SEARCH_CACHE, dict):
            SEARCH_CACHE = {}
    except Exception:
        SEARCH_CACHE = {}
else:
    SEARCH_CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(SEARCH_CACHE, f, indent=2)

# ================= HELPERS =================
def format_duration(seconds):
    try:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"
    except:
        return None

# ================= CORS =================
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
        "endpoints": {
            "search": "/search?q=",
            "audio": "/audio?url=",
            "mix": "/mix"
        }
    }

# ================= SEARCH =================
@app.get("/search")
def search(q: str = Query(...)):
    key = q.strip().lower()

    if key in SEARCH_CACHE:
        return {"query": q, "cached": True, "results": SEARCH_CACHE[key]}

    try:
        cmd = [
            YTDLP,
            "--quiet",
            "--no-warnings",
            "--skip-download",
            "--socket-timeout", "10",
            "--print",
            "%(title)s||%(id)s||%(duration)s",
            f"ytsearch1:{q}"
        ]

        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

        results = []
        for line in p.stdout.strip().split("\n"):
            if "||" not in line:
                continue

            title, vid, duration = line.split("||", 2)
            results.append({
                "title": title,
                "url": f"https://youtu.be/{vid}",
                "duration": format_duration(duration),
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            })

        if not results:
            return JSONResponse({"error": "no_results"}, status_code=404)

        SEARCH_CACHE[key] = results
        save_cache()

        return {"query": q, "cached": False, "results": results}

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "search_timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": "search_failed", "detail": str(e)}, status_code=500)

# ================= AUDIO =================
@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    try:
        now = time.time()

        if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
            stream_url = AUDIO_CACHE[url]["stream"]
        else:
            cmd = [
                YTDLP,
                "--cookies", COOKIES,
                "--force-ipv4",
                "--quiet",
                "--no-warnings",
                "--no-playlist",
                "--socket-timeout", "10",
                "-f", "140",
                "-g",
                url
            ]

            p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            stream_url = p.stdout.strip()

            if not stream_url.startswith("http"):
                return JSONResponse({"error": "stream_failed"}, status_code=500)

            AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/"
        }

        if request.headers.get("range"):
            headers["Range"] = request.headers["range"]

        r = requests.get(stream_url, headers=headers, stream=True, timeout=10)

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": r.headers.get("Content-Type", "audio/mp4")
        }

        if "Content-Length" in r.headers:
            resp_headers["Content-Length"] = r.headers["Content-Length"]
        if "Content-Range" in r.headers:
            resp_headers["Content-Range"] = r.headers["Content-Range"]

        return StreamingResponse(
            r.iter_content(chunk_size=1024 * 64),
            status_code=206 if "Range" in headers else 200,
            headers=resp_headers
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ================= MIX (TOP 5 MOST VIEWED – FIXED) =================
@app.get("/mix")
def mix():
    return {
        "type": "mix",
        "count": 10,
        "results": [
            {
                "title": "Shakira – Waka Waka",
                "url": "https://youtu.be/pRpeEdMmmQ0",
                "thumbnail": "https://i.ytimg.com/vi/pRpeEdMmmQ0/hqdefault.jpg",
                "duration": "3:31"
            },
            {
                "title": "Ed Sheeran – Shape of You",
                "url": "https://youtu.be/JGwWNGJdvx8",
                "thumbnail": "https://i.ytimg.com/vi/JGwWNGJdvx8/hqdefault.jpg",
                "duration": "3:53"
            },
            {
                "title": "Luis Fonsi – Despacito",
                "url": "https://youtu.be/kJQP7kiw5Fk",
                "thumbnail": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
                "duration": "3:48"
            }
            // 👉 aise hi 10 daal de
        ]
    }
