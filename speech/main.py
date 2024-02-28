from fastapi import FastAPI, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
import uvicorn
import os
import json

from openai import OpenAI
from pytube import YouTube

from webvtt import WebVTT, Caption
from datetime import timedelta

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")
api_key = os.environ.get("API_KEY")

# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
# client = OpenAI(api_key=OPENAI_API_KEY)


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


def generate_vtt(transcript: list[dict[str, str]]) -> WebVTT:
    subtitles = WebVTT()
    for s in transcript:
        start = str(0) + str(timedelta(seconds=int(s["start"]))) + ".000"
        end = str(0) + str(timedelta(seconds=int(s["end"]))) + ".000"
        text = s["text"]
        caption = Caption(start, end, text)
        subtitles.captions.append(caption)
    with open("temp.vtt", "w") as f:
        subtitles.write(f)
    return subtitles


@app.get("/translate")
async def translate_audio(
    video_url: str,
    api_key: str = Security(get_api_key),
    test: bool = True,
) -> FileResponse:
    if test:
        with open("test.json", "r") as f:
            file = json.load(f)
        _ = generate_vtt(file)
        return FileResponse("temp.vtt")

    try:
        yt = YouTube(video_url)
        audio = yt.streams.filter(only_audio=True).first()
        audio.download(filename="temp.mp4")
    except:
        raise HTTPException(status_code=404, detail=f"Cannot find with {video_url} url")

    audio_file = open("temp.mp4", "rb")
    transcript = client.audio.translations.create(
        model="whisper-1", file=audio_file, response_format="verbose_json"
    )
    _ = generate_vtt(transcript)
    return FileResponse("temp.vtt")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
