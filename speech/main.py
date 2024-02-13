from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from transformers import SeamlessM4Tv2Model, AutoProcessor
import torch
import torchaudio
import uvicorn
import scipy

app = FastAPI()

model = SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large")
processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large")
device = "cuda:0" if torch.cuda.is_available() else "cpu"
model = model.to(device)

SAMPLE_RATE = 16000


@app.post("/translate", response_class=FileResponse)
async def translate_audio(audio_file: UploadFile = File(...)) -> FileResponse:
    # Save the uploaded audio file
    with open("temp_audio.wav", "wb") as f:
        f.write(await audio_file.read())

    waveform, sample_rate = torchaudio.load("temp_audio.wav")
    if sample_rate != SAMPLE_RATE:
        waveform = torchaudio.functional.resample(
            waveform, orig_freq=sample_rate, new_freq=model.config.sampling_rate
        )
    audio_inputs = processor(audios=waveform, return_tensors="pt").to(device)

    output_tokens = (
        model.generate(**audio_inputs, tgt_lang="eng")[0].cpu().numpy().squeeze()
    )
    scipy.io.wavfile.write(
        "new_audio.wav",
        rate=SAMPLE_RATE,
        data=output_tokens,
    )
    return FileResponse("new_audio.wav")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
