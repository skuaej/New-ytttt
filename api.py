import subprocess
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Audio Stream API")

YTDLP = "yt-dlp"
COOKIES = "cookies.txt"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "running", "endpoint": "/audio"}

@app.get("/audio")
def audio(url: str = Query(...)):
    """
    Accepts FULL YouTube URL only.
    Returns redirect to audio stream.
    """
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
