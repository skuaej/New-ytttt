import subprocess, json
from fastapi import FastAPI, Query, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Music API")

# =====================
# CONFIG
# =====================
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
API_KEY = "mysecret123"   # optional (can remove if you want)

# =====================
# CORS
# =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# UTILS
# =====================
def check_key(key: str):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# =====================
# HEALTH
# =====================
@app.get("/")
def root():
    return {"status": "running"}

# =====================
# SEARCH META (title + thumbnail)
# =====================
@app.get("/search-meta")
def search_meta(query: str, key: str = Query(None)):
    if API_KEY:
        check_key(key)

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

        return {"status": "success", "results": results}

    except Exception as e:
        return JSONResponse(
            {"status": "error", "reason": str(e)},
            status_code=500
        )

# =====================
# SEARCH + PLAY (REDIRECT MODE)
# =====================
@app.get("/search-audio")
def search_audio(query: str, key: str = Query(None)):
    if API_KEY:
        check_key(key)

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

        # 🔥 REDIRECT (NO 403, NO CORS)
        return RedirectResponse(stream, status_code=302)

    except Exception as e:
        return JSONResponse(
            {"status": "error", "reason": str(e)},
            status_code=500
        )
