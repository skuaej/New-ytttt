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

app = FastAPI(title="YT Music API (OAuth2 Mode)")

# ================= CONFIG =================
YTDLP = "yt-dlp"
CACHE_FILE = "cache.json"

# Audio stream cache
AUDIO_CACHE = {}                 
AUDIO_CACHE_TTL = 1800           # 30 minutes

# ================= SEARCH CACHE =================
SEARCH_CACHE = {}

# ================= HELPERS =================
async def run_async_cmd(cmd):
    """Run subprocess asynchronously"""
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
    return {"status": "running", "mode": "oauth2"}

# ================= SEARCH (Telegram Bot Style) =================
@app.get("/search")
async def search(q: str = Query(...)):
    key = q.strip().lower()

    if key in SEARCH_CACHE:
        return {"query": q, "cached": True, "results": SEARCH_CACHE[key]}

    try:
        search = VideosSearch(q, limit=1)
        result = await search.next()
        data = result.get("result", [])
        
        if not data:
            return JSONResponse({"error": "no_results"}, status_code=404)

        formatted_results = []
        for item in data:
            duration_text = item.get("duration")
            formatted_results.append({
                "title": item.get("title"),
                "url": item.get("link"),
                "duration": duration_text,
                "thumbnail": item.get("thumbnails", [{}])[0].get("url").split("?")[0],
                "id": item.get("id")
            })

        SEARCH_CACHE[key] = formatted_results
        return {"query": q, "cached": False, "results": formatted_results}

    except Exception as e:
        return JSONResponse({"error": "search_failed", "detail": str(e)}, status_code=500)

# ================= AUDIO (OAuth2 Fix) =================
@app.get("/audio")
async def audio(request: Request, url: str = Query(...)):
    now = time.time()
    
    if url in AUDIO_CACHE and now - AUDIO_CACHE[url]["ts"] < AUDIO_CACHE_TTL:
        stream_url = AUDIO_CACHE[url]["stream"]
    else:
        # 🔥 THE FIX: Use OAuth2 instead of Cookies
        cmd = [
            YTDLP,
            "--username", "oauth2",  # <--- Request OAuth login
            "--password", "",        # <--- Empty password
            "--force-ipv4",
            "--quiet", 
            "--no-warnings",
            "-f", "140", 
            "-g",        
            url
        ]
        
        stdout, stderr = await run_async_cmd(cmd)
        stream_url = stdout

        # 🔥 IMPORTANT: Catch the Login Code
        if "google.com/device" in stderr:
            print(f"⚠️ ACTION REQUIRED: {stderr}") # Print to Heroku logs
            return JSONResponse({
                "error": "auth_required", 
                "message": "Check Heroku Logs! You need to authorize the server once."
            }, status_code=500)

        if not stream_url.startswith("http"):
            print(f"ERROR: {stderr}")
            return JSONResponse({"error": "stream_failed", "details": stderr}, status_code=500)

        AUDIO_CACHE[url] = {"stream": stream_url, "ts": now}

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
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
