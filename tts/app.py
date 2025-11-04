import os
from fastapi import FastAPI, Query, Response, HTTPException
from piper import PiperVoice
from pathlib import Path
import io
import wave
import logging
from pydantic import BaseModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Choose a default voice via env; you can pass a different one per request
DEFAULT_VOICE = os.getenv("PIPER_VOICE", "en_US-amy-medium")
VOICES_DIR = Path("/voices")
VOICES_DIR.mkdir(parents=True, exist_ok=True)

_voice_cache = {}


class SpeechReq(BaseModel):
    model: str | None = None  # WebUI sends e.g. "tts-1-hd" (we ignore)
    voice: str | None = None  # maps to your Piper voice basename
    input: str  # text to speak
    format: str | None = "wav"  # keep "wav" for now


@app.post("/v1/audio/speech")
def openai_audio_speech(body: SpeechReq):
    try:
        logger.info(
            f"TTS request - model: {body.model}, voice: {body.voice}, input length: {len(body.input)}"
        )

        # Decide which voice to use
        voice = body.voice or DEFAULT_VOICE
        logger.info(f"Using voice: {voice}")

        v = load_voice(voice)

        # Synthesize to WAV using wave module
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav_file:
            v.synthesize_wav(body.input, wav_file)

        # Get the audio data
        audio = buf.getvalue()

        logger.info(f"Successfully generated {len(audio)} bytes of audio")
        return Response(content=audio, media_type="audio/wav")

    except FileNotFoundError as e:
        logger.error(f"Voice file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating speech: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generating speech: {str(e)}"
        )


def load_voice(name: str) -> PiperVoice:
    """
    Load a Piper voice from /voices. Expects two files:
      - <name>.onnx
      - <name>.onnx.json
    Example: en_US-amy-medium.onnx and en_US-amy-medium.onnx.json
    """
    key = name.lower()
    if key in _voice_cache:
        return _voice_cache[key]

    onnx = VOICES_DIR / f"{name}.onnx"
    cfg = VOICES_DIR / f"{name}.onnx.json"
    if not onnx.exists() or not cfg.exists():
        raise FileNotFoundError(
            f"Voice files not found for '{name}'. "
            f"Put {onnx.name} and {cfg.name} in /voices."
        )

    v = PiperVoice.load(str(onnx), config_path=str(cfg))
    _voice_cache[key] = v
    return v


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/tts")
async def tts(
    text: str = Query(..., description="Text to synthesize"),
    voice: str = Query(
        DEFAULT_VOICE,
        description="Voice basename without extension, e.g. en_US-amy-medium",
    ),
    length_scale: float = Query(1.0),
    noise_scale: float = Query(0.667),
    noise_w: float = Query(0.8),
    sample_rate: int | None = Query(None, description="Override sample rate (Hz)"),
):
    # Load voice
    v = load_voice(voice)

    # Synthesize to a buffer (WAV)
    buf = io.BytesIO()
    v.synthesize(
        text,
        wav_file=buf,  # write wav to BytesIO
        length_scale=length_scale,
        noise_scale=noise_scale,
        noise_w=noise_w,
        sample_rate=sample_rate,
    )
    data = buf.getvalue()

    return Response(content=data, media_type="audio/wav")
