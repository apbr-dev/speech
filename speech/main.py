from fastapi import FastAPI, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from pydantic import BaseModel
import uvicorn
import os
import json
import shutil


from speech.utils import (
    generate_vtt,
    download_video,
    transcribe_audio,
    subtitle_generator_stream,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key")
api_key = os.environ.get("API_KEY")


class ReturnTranscript(BaseModel):
    id: int
    start: float
    end: float
    text: str


def get_api_key(api_key_header: str = Security(api_key_header)) -> str:
    if api_key_header == api_key:
        return api_key_header
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API Key",
    )


@app.get("/translate")
async def translate_audio(
    video_url: str,
    api_key: str = Security(get_api_key),
    test: bool = True,
) -> FileResponse:
    if test:
        with open("test.json", "r") as f:
            file = json.load(f)
        generate_vtt(file, fid="temp", save=False)
        return FileResponse("temp.vtt")
    try:
        fid = download_video(video_url)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Cannot find with {video_url} url")

    transcript = transcribe_audio(filename=f"files/{fid}/audio.mp4")
    generate_vtt(transcript.segments, fid=fid, save=True)
    return FileResponse(
        f"files/{fid}/subtitles.vtt",
        background=BackgroundTask(shutil.rmtree, f"files/{fid}"),
    )


@app.get("/translate/stream")
async def streaming_response(
    video_url: str,
    num_parts: int = 3,
):
    try:
        fid = download_video(video_url)
    except HTTPException:
        raise HTTPException(status_code=404, detail=f"Cannot find with {video_url} url")

    return StreamingResponse(
        subtitle_generator_stream(fid=fid, num_parts=num_parts),
        media_type="text/vtt",
        background=BackgroundTask(shutil.rmtree, f"files/{fid}"),
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENV") == "DEV" else False,
    )
