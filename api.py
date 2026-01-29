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
# Set to None to avoid crashes if file is missing. 
# If you DO have a working cookies.txt, change this back to "cookies.txt"
COOKIES = None 
CACHE_FILE = "cache.json"

# Audio stream cache (URL → signed stream)
AUDIO_CACHE = {}                 # { yt_url: { "stream": url, "ts": time } }
AUDIO_CACHE_TTL = 1800           # 30 minutes

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
    except Exception:
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
            "audio": "/audio?url="
        }
    }

# ================= SEARCH (FAST + SPOTIFY STYLE) =================
@app.get("/search")
def search(q: str = Query(...)):
    key = q.strip().lower()

    # 🔥 Cache hit (instant)
    if key in SEARCH_CACHE and isinstance(SEARCH_CACHE[key], list):
        return {
            "query": q,
            "cached": True,
            "results": SEARCH_CACHE[key]
        }

    try:
        cmd = [
            YTDLP,
            "--quiet",
            "--no-warnings",
            "--skip-download",
            "--socket-timeout", "10",
            "--print",
            "%(title)s||%(id)s||%(duration)s",
            f"ytsearch1:{q}"        # 🔥 only 1 result (FASTEST)
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        results = []
        for line in p.stdout.strip().split("\n"):
            if "||" not in line:
                continue

            title, vid, duration = line.split("||", 2)

            results.append({
                "title": title,
                "url": f"https://youtu.be/{vid}",
                "duration_sec": int(duration) if duration.isdigit() else None,
                "duration": format_duration(duration),
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            })

        if not results:
            return JSONResponse({"error": "no_results"}, status_code=404)

        SEARCH_CACHE[key] = results
        save_cache()

        return {
            "query": q,
            "cached": False,
            "results": results
        }

    except subprocess.TimeoutExpired:
        return JSONResponse({"error": "search_timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse({"error": "search_failed", "detail": str(e)}, status_code=500)

# ================= AUDIO (FAST + RANGE SEEK) =================
@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    try:
        now = time.time()
        stream_url = None

        # 🔥 Cache hit (instant play)
        if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
            stream_url = AUDIO_CACHE[url]["stream"]

        # Cache miss → yt-dlp
        if not stream_url:
            cmd = [
                YTDLP,
                # 🔥 FIX 1: Android Client Bypass (Tricks YouTube)
                "--extractor-args", "youtube:player_client=android",
                "--force-ipv4",
                "--quiet",
                "--no-warnings",
                "--no-playlist",
                "--socket-timeout", "10",
                "--geo-bypass",
                "--geo-bypass-country", "US",
                "-f", "140",          # m4a = fastest
                "-g",
                url
            ]

            # Add cookies ONLY if configured
            if COOKIES:
                cmd.insert(1, "--cookies")
                cmd.insert(2, COOKIES)

            p = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20 # Increased timeout slightly
            )

            stream_url = p.stdout.strip()
            
            # 🔥 FIX 2: Debugging Logs (Prints error to Heroku logs if it fails)
            if not stream_url.startswith("http"):
                print(f"ERROR STDERR: {p.stderr}")
                print(f"ERROR STDOUT: {p.stdout}")
                return JSONResponse({
                    "error": "stream_failed", 
                    "details": "Check Heroku logs for stderr output"
                }, status_code=500)

            AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

        # ===== Proxy stream with RANGE (progress bar works) =====
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/"
        }

        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        r = requests.get(stream_url, headers=headers, stream=True, timeout=10)

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": r.headers.get("Content-Type", "audio/mp4")
        }

        if "Content-Length" in r.headers:
            resp_headers["Content-Length"] = r.headers["Content-Length"]
        if "Content-Range" in r.headers:
            resp_headers["Content-Range"] = r.headers["Content-Range"]

        status_code = 206 if range_header else 200

        return StreamingResponse(
            r.iter_content(chunk_size=1024 * 64),
            status_code=status_code,
            headers=resp_headers
        )

    except Exception as e:
        # Print actual python error to logs
        print(f"PYTHON ERROR: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)
