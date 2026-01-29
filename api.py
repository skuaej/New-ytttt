import asyncio
import json
import os
import time
import subprocess
import requests

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from youtubesearchpython.__future__ import VideosSearch

app = FastAPI(title="YT Music API (Telegram Bot Style)")

# ================= CONFIG =================
YTDLP = "yt-dlp"
COOKIES = None  # Set to "cookies.txt" if you upload a valid file
CACHE_FILE = "cache.json"

# Audio stream cache
AUDIO_CACHE = {}                 
AUDIO_CACHE_TTL = 1800           # 30 minutes

# ================= SEARCH CACHE =================
SEARCH_CACHE = {}

def save_cache():
    # Simple in-memory cache save (optional expansion to file)
    pass

# ================= HELPERS =================
def format_duration(seconds):
    try:
        if not seconds: return None
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        return f"{m}:{s:02d}"
    except:
        return None

async def run_async_cmd(cmd):
    """Run subprocess asynchronously (like the Telegram bot)"""
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

# ================= SEARCH (Identical to Telegram Bot) =================
@app.get("/search")
async def search(q: str = Query(...)):
    key = q.strip().lower()

    # 1. Check Cache
    if key in SEARCH_CACHE:
        return {"query": q, "cached": True, "results": SEARCH_CACHE[key]}

    try:
        # 🔥 USE TELEGRAM BOT METHOD: VideosSearch
        search = VideosSearch(q, limit=1)
        result = await search.next()
        
        data = result.get("result", [])
        
        if not data:
            return JSONResponse({"error": "no_results"}, status_code=404)

        # Format results exactly like the bot does
        formatted_results = []
        for item in data:
            duration_text = item.get("duration")
            # Convert "MM:SS" string to seconds roughly
            duration_sec = 0
            if duration_text:
                parts = duration_text.split(":")
                if len(parts) == 2:
                    duration_sec = int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    duration_sec = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])

            formatted_results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "duration_sec": duration_sec,
                "duration": duration_text,
                "thumbnail": item.get("thumbnails", [{}])[0].get("url").split("?")[0],
                "id": item.get("id")
            })

        SEARCH_CACHE[key] = formatted_results
        return {"query": q, "cached": False, "results": formatted_results}

    except Exception as e:
        return JSONResponse({"error": "search_failed", "detail": str(e)}, status_code=500)

# ================= AUDIO (With Android Bypass) =================
@app.get("/audio")
async def audio(request: Request, url: str = Query(...)):
    now = time.time()
    
    # 1. Check Cache
    if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
        stream_url = AUDIO_CACHE[url]["stream"]
    else:
        # 2. Extraction using yt-dlp with Android Bypass
        cmd = [
            YTDLP,
            "--extractor-args", "youtube:player_client=android", # 🔥 THE FIX
            "--force-ipv4",
            "--quiet", 
            "--no-warnings",
            "-f", "140", # Best audio (m4a)
            "-g",        # Get URL only
            url
        ]
        
        if COOKIES:
            cmd.insert(1, "--cookies")
            cmd.insert(2, COOKIES)

        # Run extraction
        stdout, stderr = await run_async_cmd(cmd)
        stream_url = stdout

        if not stream_url.startswith("http"):
            print(f"ERROR: {stderr}")
            return JSONResponse({"error": "stream_failed", "details": stderr}, status_code=500)

        # Cache the result
        AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

    # 3. Stream the Audio (Proxy)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        
        # Handle seeking (Range headers)
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
