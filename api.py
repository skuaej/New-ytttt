import asyncio
import json
import os
import time
import requests

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from youtubesearchpython.__future__ import VideosSearch

app = FastAPI(title="YT Music API (Telegram Bot Style)")

# ================= CONFIG =================
YTDLP = "yt-dlp"
COOKIES_FILE = "cookies.txt"  # Ensure this file exists in your repo
CACHE_FILE = "cache.json"

# Audio stream cache
AUDIO_CACHE = {}                 
AUDIO_CACHE_TTL = 1800 

# ================= SEARCH CACHE =================
SEARCH_CACHE = {}

# ================= HELPERS =================
async def run_async_cmd(cmd):
    """
    Runs commands asynchronously, exactly like the Telegram bot's _exec_proc
    """
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    return stdout.decode().strip(), stderr.decode().strip()

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "running", "mode": "telegram_bot_style"}

# ================= SEARCH (Uses youtube-search-python) =================
@app.get("/search")
async def search(q: str = Query(...)):
    key = q.strip().lower()
    if key in SEARCH_CACHE:
        return {"query": q, "cached": True, "results": SEARCH_CACHE[key]}

    try:
        # 🔥 Exact logic from Telegram Bot's "cached_youtube_search"
        search = VideosSearch(q, limit=1)
        result = await search.next()
        data = result.get("result", [])
        
        if not data:
            return JSONResponse({"error": "no_results"}, status_code=404)

        formatted_results = []
        for item in data:
            formatted_results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "duration": item.get("duration"),
                "thumbnail": item.get("thumbnails", [{}])[0].get("url").split("?")[0],
                "id": item.get("id")
            })

        SEARCH_CACHE[key] = formatted_results
        return {"query": q, "cached": False, "results": formatted_results}

    except Exception as e:
        return JSONResponse({"error": "search_failed", "detail": str(e)}, status_code=500)

# ================= AUDIO (Uses yt-dlp + cookies.txt) =================
@app.get("/audio")
async def audio(request: Request, url: str = Query(...)):
    now = time.time()
    
    # 1. Check Cache
    if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
        stream_url = AUDIO_CACHE[url]["stream"]
    else:
        # 2. Extract using yt-dlp (Telegram Bot Style)
        cmd = [
            YTDLP,
            "--cookies", COOKIES_FILE, # 🔥 Uses your uploaded cookies.txt
            "--force-ipv4",
            "--quiet", 
            "--no-warnings",
            "-f", "140", # Best audio m4a
            "-g",        # Generator URL only
            url
        ]
        
        stdout, stderr = await run_async_cmd(cmd)
        stream_url = stdout

        # 🔥 Error Handling (Prints to Heroku Logs)
        if not stream_url.startswith("http"):
            print(f"ERROR_STDERR: {stderr}") 
            return JSONResponse({
                "error": "stream_failed", 
                "details": "Check Heroku Logs for specific error code."
            }, status_code=500)

        AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

    # 3. Stream the Audio (Proxy)
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        r = requests.get(stream_url, headers=headers, stream=True, timeout=10)
        
        resp_headers = {
            "Content-Type": "audio/mp4",
            "Accept-Ranges": "bytes"
        }
        if "Content-Length" in r.headers:
            resp_headers["Content-Length"] = r.headers["Content-Length"]
        if "Content-Range" in r.headers:
            resp_headers["Content-Range"] = r.headers["Content-Range"]

        return StreamingResponse(
            r.iter_content(chunk_size=64 * 1024),
            status_code=206 if range_header else 200,
            headers=resp_headers
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
