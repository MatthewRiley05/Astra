import os
import io
import wave
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Query, Response, HTTPException
from piper import PiperVoice
from pydantic import BaseModel

app = FastAPI(title="Piper TTS API")

# Config
DEFAULT_VOICE = os.getenv("PIPER_VOICE", "en_US-amy-medium")
VOICES_DIR = Path("/voices")
VOICES_DIR.mkdir(parents=True, exist_ok=True)
_voice_cache = {}


class SpeechReq(BaseModel):
    model: Optional[str] = None
    voice: Optional[str] = None
    input: str


def load_voice(name: str) -> PiperVoice:
    if name.lower() in _voice_cache:
        return _voice_cache[name.lower()]

    onnx, cfg = VOICES_DIR / f"{name}.onnx", VOICES_DIR / f"{name}.onnx.json"
    if not onnx.exists() or not cfg.exists():
        raise FileNotFoundError(f"Voice '{name}' not found in /voices")

    voice = PiperVoice.load(str(onnx), config_path=str(cfg))
    _voice_cache[name.lower()] = voice
    return voice


def synthesize(voice: PiperVoice, text: str, **kwargs) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        voice.synthesize_wav(text, wav, **kwargs)
    return buf.getvalue()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/audio/speech")
def audio_speech(body: SpeechReq):
    try:
        voice = load_voice(body.voice or DEFAULT_VOICE)
        audio = synthesize(voice, body.input)
        return Response(content=audio, media_type="audio/wav")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"TTS error: {str(e)}")


@app.post("/tts")
def tts(
    text: str = Query(...),
    voice: str = Query(DEFAULT_VOICE),
    length_scale: float = Query(1.0),
    noise_scale: float = Query(0.667),
    noise_w: float = Query(0.8),
    sample_rate: Optional[int] = Query(None),
):
    try:
        v = load_voice(voice)
        buf = io.BytesIO()
        v.synthesize(
            text,
            wav_file=buf,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
            sample_rate=sample_rate,
        )
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"TTS error: {str(e)}")
