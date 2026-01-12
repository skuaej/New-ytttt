import time
import psutil
import subprocess
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Stream API")

# ==========================
# CORS (safe even with redirect)
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

START_TIME = time.time()

# ==========================
# CONFIG
# ==========================
YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
MAX_VIDEO_QUALITY = "360p"

# ==========================
# UTILS
# ==========================
def uptime():
    s = int(time.time() - START_TIME)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h}h {m}m {s}s"


def load_level(cpu):
    if cpu < 40:
        return "LOW"
    elif cpu < 70:
        return "MEDIUM"
    return "HIGH"

# ==========================
# HEALTH
# ==========================
@app.get("/")
async def root():
    return {
        "status": "running",
        "uptime": uptime(),
        "endpoints": ["/audio", "/video", "/status", "/ping"]
    }

@app.get("/ping")
async def ping():
    return {"ping": "pong", "uptime": uptime()}

# ==========================
# STATUS
# ==========================
@app.get("/status")
async def status():
    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    return {
        "cpu": cpu,
        "ram_percent": ram.percent,
        "policy": {
            "video_allowed": cpu < 80,
            "max_video_quality": MAX_VIDEO_QUALITY
        }
    }

# ==========================
# AUDIO (REDIRECT MODE ✅)
# ==========================
@app.get("/audio")
async def audio(url: str = Query(...)):
    try:
        cmd = [
            YTDLP,
            "--cookies", COOKIES,
            "--force-ipv4",
            "-f", "bestaudio",
            "-g",
            url
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        stream = proc.stdout.strip()
        if not stream:
            return JSONResponse(
                {"status": "error", "reason": "audio_not_found"},
                status_code=500
            )

        # 🔥 PRODUCTION FIX: REDIRECT
        return RedirectResponse(
            url=stream,
            status_code=302
        )

    except Exception as e:
        return JSONResponse(
            {"status": "error", "reason": str(e)},
            status_code=500
        )

# ==========================
# VIDEO (OPTIONAL, 360p)
# ==========================
@app.get("/video")
async def video(url: str = Query(...)):
    cpu = psutil.cpu_percent(interval=0.3)
    if cpu > 80:
        return JSONResponse(
            {"status": "blocked", "reason": "high_cpu"},
            status_code=503
        )

    try:
        cmd = [
            YTDLP,
            "--cookies", COOKIES,
            "--force-ipv4",
            "-f", "bv*[height<=360]+ba/b",
            "-g",
            url
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25
        )

        stream = proc.stdout.strip()
        if not stream:
            return JSONResponse(
                {"status": "error", "reason": "video_not_found"},
                status_code=500
            )

        return RedirectResponse(
            url=stream,
            status_code=302
        )

    except Exception as e:
        return JSONResponse(
            {"status": "error", "reason": str(e)},
            status_code=500
        )
