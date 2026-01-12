import subprocess, time, json, os, requests
from fastapi import FastAPI, Query
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

YTDLP = "yt-dlp"
COOKIES = "cookies.txt"
CACHE_FILE = "cache.json"

STREAM_TTL = 300

# ---------- LOAD CACHE ----------
if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r") as f:
        VIDEO_CACHE = json.load(f)
else:
    VIDEO_CACHE = {}

STREAM_CACHE = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(VIDEO_CACHE, f)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- ONLY ENDPOINT ----------
@app.get("/search-audio")
def search_audio(query: str = Query(...)):
    q = query.strip().lower()

    # 1) videoId cache
    video_id = VIDEO_CACHE.get(q)

    # 2) external search (FAST)
    if not video_id:
        try:
            r = requests.get(
                "https://piped.video/api/search",
                params={"q": query, "type": "video", "region": "IN"},
                timeout=5
            )
            data = r.json()
            if data.get("items"):
                video_id = data["items"][0]["url"].split("v=")[1]
                VIDEO_CACHE[q] = video_id
                save_cache()
        except Exception:
            video_id = None

    # 3) fallback yt-dlp search
    if not video_id:
        cmd = [
            YTDLP,
            "--cookies", COOKIES,
            "--print", "%(id)s",
            "ytsearch1:" + query
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        video_id = p.stdout.strip()
        if not video_id:
            return JSONResponse({"error": "no_video"}, status_code=500)

        VIDEO_CACHE[q] = video_id
        save_cache()

    # 4) stream cache
    if video_id in STREAM_CACHE:
        stream, ts = STREAM_CACHE[video_id]
        if time.time() - ts < STREAM_TTL:
            return RedirectResponse(stream, status_code=302)

    # 5) generate stream
    cmd = [
        YTDLP,
        "--cookies", COOKIES,
        "--force-ipv4",
        "-f", "bestaudio",
        "-g",
        f"https://www.youtube.com/watch?v={video_id}"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    stream = p.stdout.strip()

    if not stream:
        return JSONResponse({"error": "no_stream"}, status_code=500)

    STREAM_CACHE[video_id] = (stream, time.time())
    return RedirectResponse(stream, status_code=302)
