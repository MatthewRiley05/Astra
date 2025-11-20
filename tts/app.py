import os
import io
import wave
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Response, HTTPException
from piper import PiperVoice
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Piper TTS API", version="0.1.0")

# Configuration
DEFAULT_VOICE = os.getenv("PIPER_VOICE", "en_US-amy-medium")
VOICES_DIR = Path("/voices")
VOICES_DIR.mkdir(parents=True, exist_ok=True)

# Voice cache for performance
_voice_cache = {}


class SpeechReq(BaseModel):
    """OpenAI-compatible speech request."""

    model: Optional[str] = None  # WebUI sends e.g. "tts-1-hd" (ignored)
    voice: Optional[str] = None  # maps to Piper voice basename
    input: str  # text to speak
    format: Optional[str] = "wav"  # keep "wav" for now


def load_voice(name: str) -> PiperVoice:
    """
    Load a Piper voice from /voices with caching.
    Expects two files: <name>.onnx and <name>.onnx.json
    """
    key = name.lower()
    if key in _voice_cache:
        logger.debug(f"Using cached voice: {name}")
        return _voice_cache[key]

    onnx = VOICES_DIR / f"{name}.onnx"
    cfg = VOICES_DIR / f"{name}.onnx.json"

    if not onnx.exists() or not cfg.exists():
        raise FileNotFoundError(
            f"Voice files not found for '{name}'. "
            f"Put {onnx.name} and {cfg.name} in /voices."
        )

    logger.info(f"Loading voice: {name}")
    v = PiperVoice.load(str(onnx), config_path=str(cfg))
    _voice_cache[key] = v
    return v


def synthesize_to_wav(voice: PiperVoice, text: str, **kwargs) -> bytes:
    """Synthesize text to WAV audio bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file, **kwargs)
    return buf.getvalue()


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"ok": True}


@app.post("/v1/audio/speech")
def openai_audio_speech(body: SpeechReq):
    """OpenAI-compatible text-to-speech endpoint."""
    try:
        logger.info(
            f"TTS request - model: {body.model}, voice: {body.voice}, "
            f"input length: {len(body.input)}"
        )

        # Determine which voice to use
        voice_name = body.voice or DEFAULT_VOICE
        logger.debug(f"Using voice: {voice_name}")

        # Load voice and synthesize
        voice = load_voice(voice_name)
        audio = synthesize_to_wav(voice, body.input)

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


@app.post("/tts")
async def tts(
    text: str = Query(..., description="Text to synthesize"),
    voice: str = Query(
        DEFAULT_VOICE,
        description="Voice basename without extension, e.g. en_US-amy-medium",
    ),
    length_scale: float = Query(1.0, description="Speech speed multiplier"),
    noise_scale: float = Query(0.667, description="Phoneme variance"),
    noise_w: float = Query(0.8, description="Phoneme duration variance"),
    sample_rate: Optional[int] = Query(None, description="Override sample rate (Hz)"),
):
    """Legacy TTS endpoint with advanced parameters."""
    try:
        logger.info(f"Legacy TTS request for voice: {voice}, text length: {len(text)}")

        # Load voice
        v = load_voice(voice)

        # Synthesize with custom parameters
        buf = io.BytesIO()
        v.synthesize(
            text,
            wav_file=buf,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
            sample_rate=sample_rate,
        )
        audio = buf.getvalue()

        logger.info(f"Generated {len(audio)} bytes of audio")
        return Response(content=audio, media_type="audio/wav")

    except FileNotFoundError as e:
        logger.error(f"Voice file not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error in legacy TTS: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error generating speech: {str(e)}"
        )
