import subprocess
import json
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Music Backend (Open)")

# =========================
# CONFIG
# =========================
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"   # must exist

# =========================
# CORS
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HEALTH
# =========================
@app.get("/")
def root():
    return {
        "status": "running",
        "endpoints": [
            "/search-meta",
            "/search-audio"
        ]
    }

# =========================
# SEARCH META
# title + thumbnail + duration
# =========================
@app.get("/search-meta")
def search_meta(query: str = Query(...)):
    try:
        cmd = [
            YTDLP,
            "--dump-json",
            "ytsearch5:" + query
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        results = []
        for line in p.stdout.splitlines():
            d = json.loads(line)
            results.append({
                "title": d.get("title"),
                "video_id": d.get("id"),
                "thumbnail": d.get("thumbnail"),
                "duration": d.get("duration")
            })

        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        return JSONResponse(
            {"status": "error", "reason": str(e)},
            status_code=500
        )

# =========================
# SEARCH + AUTO PLAY
# REDIRECT MODE (NO 403)
# =========================
@app.get("/search-audio")
def search_audio(query: str = Query(...)):
    try:
        cmd = [
            YTDLP,
            "--cookies", COOKIES,
            "--force-ipv4",
            "-f", "bestaudio",
            "-g",
            "ytsearch1:" + query
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        stream = p.stdout.strip()
        if not stream:
            return JSONResponse(
                {"status": "error", "reason": "no_stream"},
                status_code=500
            )

        # 🔥 REDIRECT → browser authorised → no 403
        return RedirectResponse(stream, status_code=302)

    except Exception as e:
        return JSONResponse(
            {"status": "error", "reason": str(e)},
            status_code=500
        )
