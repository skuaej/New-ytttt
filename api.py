
import subprocess
import random
from fastapi import FastAPI, Query, HTTPException

app = FastAPI(
    title="YouTube Audio API",
    description="Works with or without proxy + cookies",
    version="1.0"
)

COOKIES_FILE = "cookies.txt"
PROXY_FILE = "proxies.txt"


# -----------------------------
# Load proxies from file
# -----------------------------
def load_proxies():
    try:
        with open(PROXY_FILE, "r") as f:
            return [p.strip() for p in f if p.strip()]
    except:
        return []


# -----------------------------
# Run yt-dlp
# -----------------------------
def run_yt_dlp(url: str, proxy: str | None = None):
    cmd = [
        "yt-dlp",
        "--cookies", COOKIES_FILE,
        "--remote-components", "ejs:github",
        "-f", "bestaudio",
        "-g",
        url
    ]

    if proxy:
        cmd.insert(1, "--proxy")
        cmd.insert(2, proxy)
        cmd.insert(1, "--force-ipv4")

    try:
        output = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            timeout=25
        ).decode().strip()
        return output
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.output.decode())
    except Exception as e:
        raise RuntimeError(str(e))


# -----------------------------
# API Endpoint
# -----------------------------
@app.get("/audio")
def get_audio(url: str = Query(..., description="YouTube video URL")):

    # 1️⃣ TRY WITHOUT PROXY
    try:
        audio_url = run_yt_dlp(url)
        return {
            "success": True,
            "mode": "no_proxy",
            "audio_url": audio_url
        }
    except Exception as no_proxy_err:
        pass

    # 2️⃣ TRY WITH PROXY
    proxies = load_proxies()
    if not proxies:
        raise HTTPException(
            status_code=500,
            detail="Blocked without proxy & no proxy available"
        )

    proxy = random.choice(proxies)

    try:
        audio_url = run_yt_dlp(url, proxy)
        return {
            "success": True,
            "mode": "proxy",
            "proxy_used": proxy,
            "audio_url": audio_url
        }
    except Exception as proxy_err:
        raise HTTPException(
            status_code=500,
            detail=str(proxy_err)
        )
