import subprocess
import json
import os
import time
import requests

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Audio API")import subprocess
import json
import os
import time
import requests

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Audio API")

# ================= CONFIG =================
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"          # optional
CACHE_FILE = "cache.json"

AUDIO_CACHE = {}                # { url: {stream, ts} }
AUDIO_CACHE_TTL = 600           # 10 min

# ================= LOAD SEARCH CACHE =================
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

def format_duration(sec):
    try:
        sec = int(sec)
        m, s = divmod(sec, 60)
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
            "audio": "/audio?url="
        }
    }

# ================= SEARCH =================
@app.get("/search")
def search(q: str = Query(...)):
    key = q.lower().strip()
    if key in SEARCH_CACHE:
        return {"query": q, "cached": True, "results": SEARCH_CACHE[key]}

    try:
        cmd = [
            YTDLP,
            "--quiet",
            "--skip-download",
            "--print", "%(title)s||%(id)s||%(duration)s",
            f"ytsearch5:{q}"  # returns top 5 results
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if p.returncode != 0:
            return JSONResponse({"error": "yt-dlp_failed", "detail": p.stderr}, status_code=500)

        results = []
        for line in p.stdout.strip().split("\n"):
            if "||" not in line:
                continue
            title, vid, dur = line.split("||", 2)
            results.append({
                "title": title,
                "url": f"https://youtu.be/{vid}",
                "duration": format_duration(dur),
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            })

        if not results:
            return JSONResponse({"error": "no_results"}, status_code=404)

        SEARCH_CACHE[key] = results
        save_cache()
        return {"query": q, "cached": False, "results": results}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ================= AUDIO =================
@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    try:
        now = time.time()

        # cache hit
        if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
            stream_url = AUDIO_CACHE[url]["stream"]
        else:
            cmd = [
                YTDLP,
                "--quiet",
                "--no-warnings",
                "--no-playlist",
                "--socket-timeout", "10",
                "--force-ipv4",
                "--geo-bypass",
                "-f", "bestaudio/best",  # ✅ flexible audio format
                "-g",
                url
            ]

            if os.path.exists(COOKIES):
                cmd.insert(1, "--cookies")
                cmd.insert(2, COOKIES)

            p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if p.returncode != 0 or not p.stdout.startswith("http"):
                return JSONResponse({"error": "stream_failed", "detail": p.stderr}, status_code=500)

            stream_url = p.stdout.strip()
            AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/",
            "Origin": "https://www.youtube.com"
        }
        if request.headers.get("range"):
            headers["Range"] = request.headers["range"]

        r = requests.get(stream_url, headers=headers, stream=True, timeout=10)

        resp_headers = {
            "Content-Type": r.headers.get("Content-Type", "audio/mp4"),
            "Accept-Ranges": "bytes"
        }
        if "Content-Range" in r.headers:
            resp_headers["Content-Range"] = r.headers["Content-Range"]
        if "Content-Length" in r.headers:
            resp_headers["Content-Length"] = r.headers["Content-Length"]

        status = 206 if "Range" in headers else 200

        return StreamingResponse(r.iter_content(chunk_size=1024*64), status_code=status, headers=resp_headers)

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ================= CONFIG =================
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
CACHE_FILE = "cache.json"

AUDIO_CACHE = {}
AUDIO_CACHE_TTL = 600

# ================= LOAD SEARCH CACHE =================
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

def format_duration(sec):
    try:
        sec = int(sec)
        m, s = divmod(sec, 60)
        return f"{m}:{s:02d}"
    except:
        return None

# ================= yt-dlp BASE CMD =================
def base_ytdlp_cmd():
    cmd = [
        YTDLP,
        "--no-playlist",
        "--force-ipv4",
        "--geo-bypass",
    ]

    # ✔ WEB client only if cookies exist
    if os.path.exists(COOKIES):
        cmd += [
            "--cookies", COOKIES,
            "--extractor-args", "youtube:player_client=web"
        ]
    else:
        # ✔ ANDROID client when no cookies
        cmd += [
            "--extractor-args", "youtube:player_client=android"
        ]

    return cmd

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

# ================= SEARCH =================
@app.get("/search")
def search(q: str = Query(...)):
    key = q.lower().strip()

    if key in SEARCH_CACHE:
        return {"query": q, "cached": True, "results": SEARCH_CACHE[key]}

    cmd = base_ytdlp_cmd() + [
        "--quiet",
        "--skip-download",
        "--print",
        "%(title)s||%(id)s||%(duration)s",
        f"ytsearch1:{q}"
    ]

    p = subprocess.run(cmd, capture_output=True, text=True, timeout=20)

    if p.returncode != 0:
        return JSONResponse(
            {"error": "yt-dlp_failed", "detail": p.stderr},
            status_code=500
        )

    results = []
    for line in p.stdout.strip().split("\n"):
        if "||" not in line:
            continue
        title, vid, dur = line.split("||", 2)
        results.append({
            "title": title,
            "url": f"https://youtu.be/{vid}",
            "duration": format_duration(dur),
            "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        })

    if not results:
        return JSONResponse({"error": "no_results"}, status_code=404)

    SEARCH_CACHE[key] = results
    save_cache()

    return {"query": q, "cached": False, "results": results}

# ================= AUDIO =================
@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    try:
        now = time.time()

        if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
            stream_url = AUDIO_CACHE[url]["stream"]
        else:
            cmd = base_ytdlp_cmd() + [
                "--quiet",
                "--no-warnings",
                "-f", "bestaudio/best",
                "-g",
                url
            ]

            p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)

            if p.returncode != 0 or not p.stdout.startswith("http"):
                return JSONResponse({
                    "error": "stream_failed",
                    "detail": p.stderr
                }, status_code=500)

            stream_url = p.stdout.strip()
            AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/",
            "Origin": "https://www.youtube.com"
        }

        if request.headers.get("range"):
            headers["Range"] = request.headers["range"]

        r = requests.get(stream_url, headers=headers, stream=True, timeout=10)

        resp_headers = {
            "Content-Type": r.headers.get("Content-Type", "audio/mp4"),
            "Accept-Ranges": "bytes"
        }

        if "Content-Range" in r.headers:
            resp_headers["Content-Range"] = r.headers["Content-Range"]
        if "Content-Length" in r.headers:
            resp_headers["Content-Length"] = r.headers["Content-Length"]

        status = 206 if "Range" in headers else 200

        return StreamingResponse(
            r.iter_content(chunk_size=1024 * 64),
            status_code=status,
            headers=resp_headers
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
