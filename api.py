import requests
from fastapi import FastAPI, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Main API (Worker-based)")

# ================= CONFIG =================
WORKER_URL = "http://127.0.0.1:9000/resolve"

WORKER_TIMEOUT = 15      # 🔥 was 5 → caused errors
RETRY_ON_FAIL = 1        # retry once if worker slow

# ================= CORS =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= ROOT =================
@app.get("/")
def root():
    return {
        "status": "running",
        "endpoint": "/audio?url="
    }

# ================= AUDIO =================
@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    last_error = None

    # retry logic (1 retry)
    for _ in range(RETRY_ON_FAIL + 1):
        try:
            r = requests.get(
                WORKER_URL,
                params={"url": url},
                timeout=WORKER_TIMEOUT
            )

            data = r.json()
            if "audio" not in data:
                last_error = data
                continue

            stream_url = data["audio"]
            break

        except Exception as e:
            last_error = str(e)
            stream_url = None

    if not stream_url:
        return JSONResponse(
            {"error": "worker_timeout_or_failed", "detail": last_error},
            status_code=504
        )

    # ===== PROXY STREAM WITH RANGE =====
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/"
        }

        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        s = requests.get(
            stream_url,
            headers=headers,
            stream=True,
            timeout=10
        )

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": s.headers.get("Content-Type", "audio/mp4"),
        }

        if "Content-Length" in s.headers:
            resp_headers["Content-Length"] = s.headers["Content-Length"]
        if "Content-Range" in s.headers:
            resp_headers["Content-Range"] = s.headers["Content-Range"]

        status_code = 206 if range_header else 200

        return StreamingResponse(
            s.iter_content(chunk_size=1024 * 64),
            status_code=status_code,
            headers=resp_headers
        )

    except Exception as e:
        return JSONResponse(
            {"error": "stream_failed", "detail": str(e)},
            status_code=500
        )
