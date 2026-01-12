import requests
from fastapi import FastAPI, Query, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Main API")

WORKER_URL = "http://127.0.0.1:9000/resolve"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "running", "endpoints": ["/audio?url="]}

@app.get("/audio")
def audio(request: Request, url: str = Query(...)):
    try:
        # ask worker to resolve (FAST)
        r = requests.get(WORKER_URL, params={"url": url}, timeout=5)
        data = r.json()

        if "audio" not in data:
            return JSONResponse({"error": "worker_failed"}, status_code=500)

        stream_url = data["audio"]

        # proxy with RANGE (progress bar + seek)
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.youtube.com/"
        }

        if request.headers.get("range"):
            headers["Range"] = request.headers["range"]

        s = requests.get(stream_url, headers=headers, stream=True, timeout=10)

        resp_headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": s.headers.get("Content-Type", "audio/mp4"),
        }
        if "Content-Length" in s.headers:
            resp_headers["Content-Length"] = s.headers["Content-Length"]
        if "Content-Range" in s.headers:
            resp_headers["Content-Range"] = s.headers["Content-Range"]

        status_code = 206 if "Range" in headers else 200

        return StreamingResponse(
            s.iter_content(chunk_size=1024 * 64),
            status_code=status_code,
            headers=resp_headers
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
