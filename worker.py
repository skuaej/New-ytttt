import subprocess
import time
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="YT Worker")

YTDLP = "yt-dlp"
COOKIES = "cookies.txt"

# short cache inside worker (kept warm)
AUDIO_CACHE = {}          # { yt_url: { "stream": url, "ts": time } }
TTL = 600                 # 10 minutes

@app.get("/resolve")
def resolve(url: str = Query(...)):
    now = time.time()

    # cache hit
    if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < TTL:
        return {"audio": AUDIO_CACHE[url]["stream"], "cached": True}

    try:
        cmd = [
            YTDLP,
            "--cookies", COOKIES,
            "--force-ipv4",
            "--quiet",
            "--no-warnings",
            "--no-playlist",
            "-f", "140",        # fastest m4a
            "-g",
            url
        ]

        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        stream = p.stdout.strip()
        if not stream.startswith("http"):
            return JSONResponse({"error": "resolve_failed"}, status_code=500)

        AUDIO_CACHE[url] = {"stream": stream, "ts": now}
        return {"audio": stream, "cached": False}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
