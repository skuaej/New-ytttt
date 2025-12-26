# Authored By Certified Coders © 2025
# FastAPI YouTube Audio API
# Cookies + Proxy + Telegram Friendly

import random
import asyncio
from fastapi import FastAPI, Query, HTTPException
import yt_dlp

app = FastAPI(title="YT Audio API", version="1.0")

COOKIE_FILE = "cookies.txt"
PROXY_FILE = "proxies.txt"


# -------------------------------
# Load random proxy
# -------------------------------
def get_proxy():
    try:
        with open(PROXY_FILE, "r") as f:
            proxies = [p.strip() for p in f if p.strip()]
        return random.choice(proxies) if proxies else None
    except Exception:
        return None


# -------------------------------
# yt-dlp extractor
# -------------------------------
async def extract_audio(url: str):
    proxy = get_proxy()

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "cookiefile": COOKIE_FILE,
        "proxy": proxy,
        "nocheckcertificate": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android"],
                "skip": ["dash", "hls"]
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 13; Mobile) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36"
            )
        }
    }

    loop = asyncio.get_event_loop()

    def _run():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info["url"]

    return await loop.run_in_executor(None, _run)


# -------------------------------
# Health check
# -------------------------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "YT Audio API running"}


# -------------------------------
# Audio endpoint
# -------------------------------
@app.get("/audio")
async def audio(
    url: str = Query(..., description="YouTube video URL")
):
    try:
        audio_url = await extract_audio(url)
        return {
            "status": "success",
            "audio_url": audio_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
)
