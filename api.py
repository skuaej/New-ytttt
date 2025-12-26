import subprocess
import random
import requests
from fastapi import FastAPI, Query, Response

app = FastAPI()

COOKIES = "cookies.txt"
PROXY_FILE = "proxy.txt"


def get_proxy():
    try:
        with open(PROXY_FILE) as f:
            proxies = [p.strip() for p in f if p.strip()]
        return random.choice(proxies) if proxies else None
    except:
        return None


@app.get("/audio")
def audio(url: str = Query(...)):

    proxy = get_proxy()

    # EXACT yt-dlp command you gave
    cmd = [
        "yt-dlp",
        "--cookies", COOKIES,
        "--remote-components", "ejs:github",
        "--force-ipv4",
        "-f", "bestaudio",
        "-g", url
    ]

    if proxy:
        cmd.insert(1, "--proxy")
        cmd.insert(2, proxy)

    try:
        stream_url = subprocess.check_output(
            cmd,
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "proxy_used": proxy,
            "detail": e.output
        }

    # Browser ke liye headers
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.youtube.com/",
        "Accept": "*/*",
        "Range": "bytes=0-"
    }

    # requests SOCKS support automatically agar scheme socks4/socks5 ho
    proxies = {
        "http": proxy,
        "https": proxy
    } if proxy else None

    r = requests.get(
        stream_url,
        headers=headers,
        stream=True,
        timeout=20,
        proxies=proxies
    )

    return Response(
        r.iter_content(chunk_size=1024 * 32),
        media_type="audio/webm",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache"
        }
    )
