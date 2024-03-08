from webvtt import WebVTT, Caption
from datetime import timedelta
from pytube import YouTube
from pydub import AudioSegment
from typing import Any

import os
import shutil
from openai import OpenAI

from uuid import uuid4


OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe_audio(filename: str) -> Any:
    audio_file = open(filename, "rb")
    return client.audio.translations.create(
        model="whisper-1", file=audio_file, response_format="verbose_json"
    )


def generate_vtt(
    transcript: list[dict[str, str]],
    fid: str,
    save: bool = True,
) -> WebVTT:
    subtitles = WebVTT()
    for s in transcript:
        start = str(0) + str(timedelta(seconds=int(s["start"]))) + ".000"
        end = str(0) + str(timedelta(seconds=int(s["end"]))) + ".000"
        text = s["text"]
        caption = Caption(start, end, text)
        subtitles.captions.append(caption)
    if save:
        with open(f"files/{fid}/subtitles.vtt", "w") as f:
            subtitles.write(f)
    return subtitles


def generate_vtt_string(transcript: list[dict[str, str]], offset: float = 0) -> str:
    subtitle_string = "WEBVTT\n\n"
    for s in transcript:
        start = (
            str(0)
            + str(timedelta(seconds=int(s["start"])) + timedelta(seconds=offset))
            + ".000"
        )
        end = (
            str(0)
            + str(timedelta(seconds=int(s["end"])) + timedelta(seconds=offset))
            + ".000"
        )
        text = s["text"]
        subtitle_string += f"{start} --> {end}\n{text}\n\n"
    return subtitle_string


def download_video(video_url: str) -> str:
    yt = YouTube(video_url)
    audio = yt.streams.filter(only_audio=True).first()
    fid = str(uuid4())
    os.makedirs(f"files/{fid}")
    filename = f"files/{fid}/audio.mp4"
    audio.download(filename=filename)
    return fid


def split_audio(fid: str, output_folder: str, num_parts: int) -> list[int]:
    lengths = []
    # Load the audio file
    audio = AudioSegment.from_file(f"files/{fid}/audio.mp4")

    # Calculate the duration of each part
    part_duration = len(audio) // num_parts

    # Create the output folder if it doesn't exist
    if os.path.exists(output_folder) and os.path.isdir(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    # Split the audio into parts
    for i in range(num_parts):
        start_time = i * part_duration
        end_time = (i + 1) * part_duration

        # Extract the segment
        segment = audio[start_time:end_time]

        # Define the output file name
        output_file = os.path.join(output_folder, f"part_{i+1}.mp3")
        segment.export(output_file, format="mp3")
        lengths.append(len(segment))

    return lengths


async def subtitle_generator_stream(fid: str, num_parts: int) -> str:
    output_folder = f"files/{fid}"
    section_lengths = split_audio(
        fid=fid,
        output_folder=output_folder,
        num_parts=num_parts,
    )
    offset = 0
    for i in range(len(section_lengths)):
        transcript = transcribe_audio(f"{output_folder}/part_{i+1}.mp3")
        subtitles = generate_vtt_string(transcript.segments, offset=offset)
        offset += int(section_lengths[i] / 1000)
        yield subtitles.encode("utf-8")
