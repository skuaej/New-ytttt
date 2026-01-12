import subprocess
import requests
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="YT Music API")

YTDLP = "yt-dlp"
COOKIES = "cookies.txt"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================
# SEARCH (KEYWORD → URL)
# ======================
@app.get("/search")
def search(q: str = Query(...)):
    try:
        r = requests.get(
            "https://piped.video/api/search",
            params={"q": q, "type": "video"},
            timeout=5
        )
        data = r.json()

        if not data.get("items"):
            return JSONResponse({"error": "no_results"}, status_code=404)

        item = data["items"][0]

        return {
            "title": item.get("title"),
            "url": item.get("url")
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# ======================
# AUDIO (URL → STREAM)
# ======================
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
