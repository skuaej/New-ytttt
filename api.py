
# ================================
#  YouTube Audio API
#  Proxy + Cookies Supported
# ================================

import os
import random
import yt_dlp
from fastapi import FastAPI, HTTPException

# ---------------- CONFIG ----------------

PROXY_FILE = "proxies.txt"
COOKIE_FILE = "cookies.txt"

# ---------------------------------------

app = FastAPI(title="YT Audio API")

# ---------- PROXY HANDLER ---------------

def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, "r") as f:
        return [p.strip() for p in f if p.strip()]

PROXIES = load_proxies()

def get_proxy():
    if not PROXIES:
        return None
    return random.choice(PROXIES)

# ---------- YTDLP OPTIONS ---------------

def ydl_opts():
    proxy = get_proxy()

    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "bestaudio/best",
        "noplaylist": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
    }

    # Add proxy
    if proxy:
        opts["proxy"] = proxy

    # Add cookies
    if os.path.exists(COOKIE_FILE):
        opts["cookiefile"] = COOKIE_FILE

    return opts

# ---------- API ROUTE -------------------

@app.get("/")
def home():
    return {"status": "running"}

@app.get("/audio")
def get_audio(url: str):
    try:
        opts = ydl_opts()

        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

            audio_url = info.get("url")
            if not audio_url:
                raise Exception("Audio stream not found")

            return {
                "status": "ok",
                "title": info.get("title"),
                "duration": info.get("duration"),
                "audio_url": audio_url,
                "proxy_used": opts.get("proxy", "none"),
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
