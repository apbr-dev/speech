from fastapi import FastAPI, Security
from fastapi.security import APIKeyHeader
from fastapi.exceptions import HTTPException
from pydantic import BaseModel
import uvicorn
import os
import json

from openai import OpenAI
from pytube import YouTube

app = FastAPI()
api_key_header = APIKeyHeader(name="X-API-Key")
api_key = os.environ.get("API_KEY")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


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


@app.get("/translate", response_model=list[ReturnTranscript])
async def translate_audio(
    video_url: str,
    api_key: str = Security(get_api_key),
    test: bool = True,
) -> list[ReturnTranscript]:
    if test:
        with open("test.json", "r") as f:
            file = json.load(f)
        return [ReturnTranscript(**x) for x in file]

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
    return [ReturnTranscript(**x) for x in transcript.segments]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
