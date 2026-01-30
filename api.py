from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from yt_dlp import YoutubeDL
import os
import tempfile

app = FastAPI(title="YouTube Downloader API")

# Video download options
YDL_VIDEO_OPTS = {
    "format": "bestvideo+bestaudio/best",
    "outtmpl": "%(title)s.%(id)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "merge_output_format": "mp4",
    "restrictfilenames": True,
}

# Audio download options
YDL_AUDIO_OPTS = {
    "format": "bestaudio[ext=m4a]/bestaudio/best",
    "outtmpl": "%(title)s.%(id)s.%(ext)s",
    "noplaylist": True,
    "quiet": True,
    "restrictfilenames": True,
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ],
}

@app.get("/")
async def root():
    return {"message": "YouTube Downloader API is running", "endpoints": ["/video", "/audio"]}

@app.get("/video")
async def download_video(url: str = Query(..., description="YouTube Video URL")):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YDL_VIDEO_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(title)s.%(id)s.%(ext)s")
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            return FileResponse(filename, filename=os.path.basename(filename))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/audio")
async def download_audio(url: str = Query(..., description="YouTube Video URL")):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            opts = YDL_AUDIO_OPTS.copy()
            opts["outtmpl"] = os.path.join(tmpdir, "%(title)s.%(id)s.%(ext)s")
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = os.path.splitext(ydl.prepare_filename(info))[0] + ".mp3"
            return FileResponse(filename, filename=os.path.basename(filename))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
