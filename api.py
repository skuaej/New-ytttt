from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from yt_dlp import YoutubeDL
import io

app = FastAPI(title="YouTube Downloader API")

# Video options with safe fallback
YDL_VIDEO_OPTS = {
    "format": "bestvideo+bestaudio/best/best",  # fallback to single stream
    "noplaylist": True,
    "quiet": True,
    "merge_output_format": "mp4",
    "restrictfilenames": True,
}

# Audio options
YDL_AUDIO_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "restrictfilenames": True,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]
}

def download_to_bytes(url: str, opts: dict, ext: str):
    """
    Downloads video/audio into memory and returns BytesIO
    """
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Force download to memory using a BytesIO stream
            filename = ydl.prepare_filename(info)
            ydl.download([url])
            
            # Read file into memory
            with open(filename, "rb") as f:
                data = io.BytesIO(f.read())
            data.seek(0)
        return data, filename
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/video")
async def download_video(url: str = Query(..., description="YouTube Video URL")):
    """
    Download YouTube video and return as streaming response
    """
    data, filename = download_to_bytes(url, YDL_VIDEO_OPTS, "mp4")
    return StreamingResponse(data, media_type="video/mp4", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

@app.get("/audio")
async def download_audio(url: str = Query(..., description="YouTube Video URL")):
    """
    Download YouTube audio only and return as streaming response
    """
    data, filename = download_to_bytes(url, YDL_AUDIO_OPTS, "mp3")
    filename = filename.rsplit(".", 1)[0] + ".mp3"
    return StreamingResponse(data, media_type="audio/mpeg", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

@app.get("/")
async def root():
    return JSONResponse({
        "message": "YouTube Downloader API is running",
        "endpoints": ["/video?url=VIDEO_URL", "/audio?url=VIDEO_URL"]
    })
