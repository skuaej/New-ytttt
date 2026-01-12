import requests
import subprocess
from fastapi import FastAPI, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Main API (Worker-based + Search)")

# ================= CONFIG =================
WORKER_URL = "http://127.0.0.1:9000/resolve"
WORKER_TIMEOUT = 15
RETRY_ON_FAIL = 1

YTDLP = "yt-dlp"

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

# ================= SEARCH API =================
@app.get("/search")
def search(q: str = Query(...)):
    """
    Keyword search
    Returns: title, thumbnail, duration, youtube_url
    """
    try:
        cmd = [
            YTDLP,
            "--quiet",
            "--no-warnings",
            "--skip-download",
            "--print",
            "%(title)s||%(id)s||%(duration)s",
            f"ytsearch5:{q}"   # 5 results only (fast)
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        results = []

        for line in p.stdout.strip().split("\n"):
            if "||" not in line:
                continue

            title, vid, duration = line.split("||", 2)

            results.append({
                "title": title,
                "url": f"https://youtu.be/{vid}",
                "thumbnail": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
                "duration": int(duration) if duration.isdigit() else None
            })

        if not results:
            return JSONResponse(
                {"error": "no_results"},
                status_code=404
            )

        return {
            "query": q,
            "results": results
        }

    except subprocess.TimeoutExpired:
        return JSONResponse(
            {"error": "search_timeout"},
            status_code=504
        )
    except Exception as e:
        return JSONResponse(
            {"error": "search_failed", "detail": str(e)},
            status_code=500
        )

# ================= AUDIO =================
@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    last_error = None
    stream_url = None

    # retry logic
    for _ in range(RETRY_ON_FAIL + 1):
        try:
            r = requests.get(
                WORKER_URL,
                params={"url": url},
                timeout=WORKER_TIMEOUT
            )

            data = r.json()
            if "audio" not in data:
                last_error = data
                continue

            stream_url = data["audio"]
            break

        except Exception as e:
            last_error = str(e)

    if not stream_url:
        return JSONResponse(
            {"error": "worker_timeout_or_failed", "detail": last_error},
            status_code=504
        )

    # ===== PROXY STREAM WITH RANGE =====
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/"
        }

        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        s = requests.get(
            stream_url,
            headers=headers,
            stream=True,
            timeout=10
        )

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": s.headers.get("Content-Type", "audio/mp4"),
        }

        if "Content-Length" in s.headers:
            resp_headers["Content-Length"] = s.headers["Content-Length"]
        if "Content-Range" in s.headers:
            resp_headers["Content-Range"] = s.headers["Content-Range"]

        status_code = 206 if range_header else 200

        return StreamingResponse(
            s.iter_content(chunk_size=1024 * 64),
            status_code=status_code,
            headers=resp_headers
        )

    except Exception as e:
        return JSONResponse(
            {"error": "stream_failed", "detail": str(e)},
            status_code=500
        )
