# api.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
import os
import tempfile

app = FastAPI(title="YouTube Downloader API")

# Common yt-dlp options
YDL_OPTS = {
    "format": "bestvideo+bestaudio/best",  # automatically picks best available video+audio
    "outtmpl": "%(title)s.%(id)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "merge_output_format": "mp4",
    "restrictfilenames": True
}

AUDIO_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "outtmpl": "%(title)s.%(id)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "restrictfilenames": True,
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]
}

@app.get("/video")
async def download_video(url: str = Query(..., description="YouTube Video URL")):
    """
    Download YouTube video and return file path
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YDL_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(title)s.%(id)s.%(ext)s")
            
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)

            return FileResponse(filename, filename=os.path.basename(filename))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/audio")
async def download_audio(url: str = Query(..., description="YouTube Video URL")):
    """
    Download YouTube audio only and return file path
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = AUDIO_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(title)s.%(id)s.%(ext)s")
            
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"

            return FileResponse(filename, filename=os.path.basename(filename))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/")
async def root():
    return JSONResponse({"message": "YouTube Downloader API is running", "endpoints": ["/video", "/audio"]})
