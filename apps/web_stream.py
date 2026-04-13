
import os
import time
import asyncio
import json
import numpy as np
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn
from vieneu import Vieneu
import io
import wave
from huggingface_hub import hf_hub_download

# ==========================================
# CLONED VOICES — PERSISTED TO DISK
# ==========================================
# Allow override via environment variable for Docker/Windows sharing
_DEFAULT_CLONED_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CLONED_VOICES_FILE = os.environ.get(
    "VIENEUTTS_CLONED_VOICES_FILE",
    os.path.join(_DEFAULT_CLONED_DIR, "cloned_voices.json")
)


def _ensure_cloned_dir():
    os.makedirs(os.path.dirname(CLONED_VOICES_FILE), exist_ok=True)


def _load_cloned_voices() -> dict:
    """Load persisted cloned voices from JSON file."""
    _ensure_cloned_dir()
    if not os.path.exists(CLONED_VOICES_FILE):
        return {}
    try:
        with open(CLONED_VOICES_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return raw
    except Exception:
        return {}


def _save_cloned_voices(voices: dict) -> None:
    """Persist cloned voices to JSON file."""
    _ensure_cloned_dir()
    with open(CLONED_VOICES_FILE, "w", encoding="utf-8") as f:
        json.dump(voices, f, ensure_ascii=False)


# ── Load persisted voices into TTS global ────────────────────────────────────
def _register_cloned_voices(tts, cloned_voices: dict) -> None:
    """Register persisted voices into the live TTS instance."""
    if cloned_voices is None:
        cloned_voices = {}
    for voice_id, data in cloned_voices.items():
        try:
            codes = data.get("codes", [])
            if not codes:
                print(f"[Voice] WARNING: Cloned voice '{voice_id}' has no codes — skipping (audio may be corrupted)")
                continue
            tts._preset_voices[voice_id] = {
                "text": data.get("text", ""),
                "codes": codes,
                "description": f"Custom cloned voice for {voice_id}"
            }
            print(f"[Voice] Registered cloned voice: {voice_id} ({len(codes)} codes)")
        except Exception as e:
            print(f"[Voice] WARNING: Failed to register voice '{voice_id}': {e}")
    print(f"[Voice] Registered {len(cloned_voices)} persisted voice(s): {list(cloned_voices.keys())}")


# ==========================================
# CONFIG GGUF MODELS
# ==========================================
AVAILABLE_MODELS = {
    "q4": {
        "id": "pnnbao-ump/VieNeu-TTS-0.3B-q4-gguf",
        "name": "VieNeu 0.3B (Q4_0) - Fast/Light",
        "desc": "Recommended for most CPUs (Speed > Quality)"
    },
    "q8": {
        "id": "pnnbao-ump/VieNeu-TTS-0.3B-q8-gguf",
        "name": "VieNeu 0.3B (Q8_0) - High Quality",
        "desc": "Higher quality but slower (Requires strong CPU)"
    },
    "ngochuyen": {
        "id": "pnnbao-ump/VieNeu-TTS-0.3B-ngoc-huyen-gguf-Q4_0",
        "name": "VieNeu 0.3B (Q4_0) - Ngoc Huyen",
        "desc": "Ngoc Huyen Voice"
    }
}

DEFAULT_MODEL = "q4"

# Map model key → default voice key (case-sensitive, matches voices.json in each repo)
MODEL_DEFAULT_VOICE = {
    "ngochuyen": "NgocHuyen",   # HF repo uses "NgocHuyen" not "ngochuyen"
    "q4":        "Binh",         # generic model uses "Binh"
    "q8":        "Binh",
}
current_model_id = DEFAULT_MODEL
app = FastAPI()

# Global TTS Instance
tts = None

def load_model_instance(model_key):
    global tts, current_model_id
    print(f"⏳ Loading Model: {model_key}...")
    
    repo_id = ""
    
    # Check if this is a preset model key
    if model_key in AVAILABLE_MODELS:
        repo_id = AVAILABLE_MODELS[model_key]["id"]
    else:
        # Assume it's a custom Hugging Face Repo ID
        # Validation: Must contain 'gguf' (case-insensitive)
        if "gguf" not in model_key.lower():
            raise ValueError("Custom Model ID must contain 'gguf' (e.g. user/model-gguf)")
        
        repo_id = model_key.strip()
        print(f"🔄 Custom Model Detected: {repo_id}")

    # Reload TTS
    try:
        new_tts = Vieneu(
            mode='standard',
            backbone_repo=repo_id,
            backbone_device="cpu",
            codec_repo="neuphonic/distill-neucodec",
            codec_device="cpu"
        )
        tts = new_tts
        current_model_id = model_key
        print(f"✅ Model Loaded Successfully: {repo_id}")
    except Exception as e:
        print(f"❌ Failed to load model {repo_id}: {e}")
        raise e

# Initial Load
try:
    load_model_instance(DEFAULT_MODEL)
    # Register previously cloned voices from disk
    persisted = _load_cloned_voices()
    _register_cloned_voices(tts, persisted)
    if persisted:
        print(f"🔊 Registered {len(persisted)} persisted cloned voice(s)")
except Exception:
    print("⚠️ Initial model load failed. Server running but needs valid model.")


# ==========================================
# UI SERVING
# ==========================================
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "client.html"), "r", encoding="utf-8") as f:
        HTML_CONTENT = f.read()
    HTML_CONTENT = HTML_CONTENT.replace("VieNeu Stream", "VieNeu GGUF (CPU)")
    HTML_CONTENT = HTML_CONTENT.replace("Server: LMDeploy (Remote)", "Server: Local GGUF (CPU)")
except FileNotFoundError:
    HTML_CONTENT = "<h1>Error: client.html missing</h1>"

@app.get("/")
async def get_ui():
    return HTMLResponse(content=HTML_CONTENT)

@app.get("/models")
async def get_models():
    """Return available models"""
    return [
        {"key": k, "name": v["name"], "desc": v["desc"], "active": k == current_model_id}
        for k, v in AVAILABLE_MODELS.items()
    ]

from typing import Optional
from pydantic import BaseModel, Field
from fastapi import UploadFile, File, Form

class ModelRequest(BaseModel):
    model_key: str

class UrlRequest(BaseModel):
    url: str
    max_chars: int = Field(default=5000, le=20000)

class StreamRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None
    voice: Optional[str] = None  # Legacy field name from ai-service

@app.post("/set_model")
async def set_model(req: ModelRequest):
    """Switch Model"""
    try:
        load_model_instance(req.model_key)
        return {"status": "ok", "current_model": req.model_key}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/extract_url")
async def extract_url(req: UrlRequest):
    """Extract article text from a URL."""
    try:
        from vieneu_utils.url_extract import extract_text_from_url as _extract
        result = _extract(req.url, max_chars=req.max_chars)
    except ImportError:
        result = {"error": "URL extraction not available (trafilatura not installed)", "title": "", "text": "", "char_count": 0, "truncated": False}
    if result["error"]:
        return {"status": "error", "message": result["error"]}
    return {
        "status": "ok",
        "title": result["title"],
        "text": result["text"],
        "char_count": result["char_count"],
        "truncated": result["truncated"],
    }

@app.get("/voices")
async def get_voices():
    """Return list of available voices. If none/error, return instruction."""
    try:
        if tts is None:
             return [{"id": "error", "name": "Model not loaded yet"}]

        voices = tts.list_preset_voices()
        
        if not voices:
             # Voices.json missing or empty
             return [{"id": "error_no_voices", "name": "⚠️ ERROR: No voices found! Please create voices.json in the model folder."}]

        # Normalize to list of objects for easier JS handling
        result = []
        if isinstance(voices[0], tuple):
            for desc, vid in voices:
                result.append({"id": vid, "name": desc})
        else:
            # Fallback if list is just strings
            for vid in voices:
                result.append({"id": vid, "name": vid})
        return result
    except Exception as e:
        print(f"Error listing voices: {e}")
        return [{"id": "error_exception", "name": f"⚠️ Error loading voices: {str(e)}"}]

@app.post("/clone_voice")
async def clone_voice(voice_id: str = Form(...), ref_text: str = Form(...), file: UploadFile = File(...)):
    """Zero-shot Voice Cloning Endpoint: Upload audio and its transcript to create a dynamic voice."""
    if tts is None:
        return {"status": "error", "message": "Model not loaded yet"}

    import os as _os

    try:
        # Save temp file
        temp_file_path = f"temp_clone_{voice_id}.wav"
        with open(temp_file_path, "wb") as f:
            f.write(await file.read())
        print(f"[Clone] Audio saved to {temp_file_path}, size={_os.path.getsize(temp_file_path)} bytes")

        # Validate audio is valid
        file_size = _os.path.getsize(temp_file_path)
        if file_size < 1000:
            if _os.path.exists(temp_file_path):
                _os.remove(temp_file_path)
            return {"status": "error", "message": f"Audio file too small ({file_size} bytes). Please upload a valid audio file (at least 1KB)."}

        # Encode audio reference
        print(f"[Clone] Encoding reference for voice_id={voice_id}...")
        ref_codes = tts.encode_reference(temp_file_path)
        print(f"[Clone] encode_reference done, type={type(ref_codes)}")

        # Clean up temp file
        if _os.path.exists(temp_file_path):
            _os.remove(temp_file_path)
            print(f"[Clone] Temp file removed")

        # Convert tensor to list for JSON compatibility
        if hasattr(ref_codes, "cpu"):
            ref_codes_list = ref_codes.flatten().tolist()
        else:
            ref_codes_list = list(ref_codes) if hasattr(ref_codes, "__iter__") else ref_codes
        print(f"[Clone] ref_codes_list length={len(ref_codes_list)}")

        # Validate we got actual codes
        if len(ref_codes_list) == 0:
            return {"status": "error", "message": "Failed to encode audio. The audio file may be corrupted or in an unsupported format. Try a WAV or MP3 file recorded directly (not converted from video)."}

        # ── Guard: Reject audio that is too long ────────
        # For zero-shot cloning, ref_text MUST perfectly match the audio.
        # If we silently truncate the codes, the model hallucinates the remaining
        # ref_text into the output. Also, GGUF has a strict context limit.
        MAX_REF_CODES = 350
        if len(ref_codes_list) > MAX_REF_CODES:
            duration_sec = len(ref_codes_list) / 50.0  # Approx 50 codes per second
            return {
                "status": "error", 
                "message": f"Audio is too long ({duration_sec:.1f}s, {len(ref_codes_list)} codes). For voice cloning, please use a short clip (3-6 seconds) and ensure your ref_text EXACTLY matches every spoken word."
            }

        # ── 1. Register in-memory (for current session) ──────────────────────
        # Cloned voice codes are pure data (ref tokens), NOT model weights.
        # There is no need to reload the TTS model — just store them directly.
        tts._preset_voices[voice_id] = {
            "text": ref_text,
            "codes": ref_codes_list,
            "description": f"Custom cloned voice for {voice_id}"
        }
        print(f"[Clone] Registered in-memory: voice_id={voice_id} ({len(ref_codes_list)} codes)")

        # ── 2. Persist to disk so voices survive server restarts ──────────────
        cloned = _load_cloned_voices()
        print(f"[Clone] Loaded existing voices from disk: {list(cloned.keys())}")
        cloned[voice_id] = {
            "text": ref_text,
            "codes": ref_codes_list
        }
        _save_cloned_voices(cloned)
        print(f"[Clone] Saved voices to disk: {list(cloned.keys())}")

        return {"status": "ok", "voice_id": voice_id, "message": "Voice cloned and persisted. You can now use this voice for TTS."}
    except Exception as e:
        import traceback
        print(f"[Clone] FAILED: {e}")
        traceback.print_exc()
        return {"status": "error", "message": f"Failed to clone voice: {str(e)}"}

def float32_to_pcm16(audio_float):
    """Convert float32 [-1, 1] to int16 bytes"""
    audio_int16 = (audio_float * 32767).clip(-32768, 32767).astype(np.int16)
    return audio_int16.tobytes()


def _resolve_voice(voice_id: str | None) -> dict | None:
    """
    Resolve voice_id to TTS voice_data dict.
    Handles:
      1. Exact key match in _preset_voices
      2. Case-insensitive fallback (e.g. "ngochuyen" → "NgocHuyen")
      3. Model default voice (from MODEL_DEFAULT_VOICE)
      4. First available voice in _preset_voices
      5. None (fully default)
    """
    if not voice_id:
        voice_id = ""

    voice_data = None
    reason = "default (no voice_id)"

    if voice_id:
        reason = f"voice_id='{voice_id}'"
        try:
            voice_data = tts.get_preset_voice(voice_id)
            reason = f"exact match '{voice_id}'"
        except ValueError:
            # Key not found — try case-insensitive scan of available voices
            available = tts.list_preset_voices()  # [(desc, key), ...]
            for desc, key in available:
                if key.lower() == voice_id.lower():
                    voice_data = tts.get_preset_voice(key)
                    reason = f"case-insensitive '{voice_id}' → '{key}'"
                    break
            if voice_data is None and available:
                # voice_id sent but not found — still try model default
                model_default = MODEL_DEFAULT_VOICE.get(current_model_id)
                if model_default:
                    try:
                        voice_data = tts.get_preset_voice(model_default)
                        reason = f"model default '{model_default}' (requested '{voice_id}' not found)"
                    except ValueError:
                        pass

        if voice_data is None:
            reason = f"voice '{voice_id}' not found — using model default"
            model_default = MODEL_DEFAULT_VOICE.get(current_model_id)
            if model_default:
                try:
                    voice_data = tts.get_preset_voice(model_default)
                    reason = f"model default '{model_default}'"
                except ValueError:
                    reason = f"model default '{model_default}' also not found"
                    if tts.list_preset_voices():
                        first_key = tts.list_preset_voices()[0][1]
                        voice_data = tts.get_preset_voice(first_key)
                        reason = f"first available voice '{first_key}'"
            elif tts.list_preset_voices():
                first_key = tts.list_preset_voices()[0][1]
                voice_data = tts.get_preset_voice(first_key)
                reason = f"first available voice '{first_key}'"

    print(f"[Voice] Using {reason} | available: {[k for _, k in tts.list_preset_voices()]}")
    return voice_data


def _build_wav_header(num_samples: int, channels: int = 1, sample_width: int = 2, frame_rate: int = 24000) -> bytes:
    """Build a proper WAV RIFF header with correct data chunk size."""
    import struct
    byte_rate    = frame_rate * channels * sample_width
    block_align  = channels * sample_width
    data_size    = num_samples * block_align
    file_size    = 36 + data_size  # RIFF header total - 8

    return (
        b'RIFF' + struct.pack('<I', file_size) + b'WAVE'
        + b'fmt ' + struct.pack('<I', 16)
        + struct.pack('<HHIIHH', 1, channels, frame_rate, byte_rate, block_align, 16)
        + b'data' + struct.pack('<I', data_size)
    )


async def _do_stream(text: str, voice_id: str | None) -> StreamingResponse:
    """Shared streaming logic for GET and POST /stream."""
    voice_data = _resolve_voice(voice_id)

    # Buffer all chunks first so we can write a correct WAV header
    # (the TTS model generates everything before yielding anyway)
    MAX_BUFFER_BYTES = 100 * 1024 * 1024  # 100 MB cap

    async def audio_generator():
        all_samples: list[bytes] = []
        start = time.time()
        count = 0
        try:
            for chunk in tts.infer_stream(text, voice=voice_data):
                if count == 0:
                    print(f"⚡ First sound in {time.time() - start:.3f}s")
                count += 1
                pcm = float32_to_pcm16(chunk)
                all_samples.append(pcm)
                # Safety cap — don't buffer more than MAX_BUFFER_BYTES
                total = sum(len(p) for p in all_samples)
                if total > MAX_BUFFER_BYTES:
                    print(f"[WAV] Buffer cap reached ({total / 1024 / 1024:.1f} MB), stopping collection")
                    break
        except Exception as e:
            print(f"Error during inference: {e}")

        total_bytes = b''.join(all_samples)
        total_frames = len(total_bytes) // 2  # int16 = 2 bytes per sample
        real_header = _build_wav_header(total_frames)
        print(f"[WAV] Done: {total_frames} frames ({len(total_bytes) / 1024 / 1024:.2f} MB PCM), header {len(real_header)} bytes")
        yield real_header + total_bytes

    return StreamingResponse(audio_generator(), media_type="audio/wav")


@app.get("/stream")
async def stream_audio(text: str, voice_id: str = None):
    """Streaming Endpoint with Voice Support"""
    return await _do_stream(text, voice_id)


@app.post("/stream")
async def stream_audio_post(req: StreamRequest):
    """Streaming Endpoint via POST (for long text from URL extraction)."""
    voice_id = req.voice_id or req.voice  # Accept both field names
    return await _do_stream(req.text, voice_id)

def main():
    print("🌍 Open http://localhost:8008 to test GGUF Streaming")
    uvicorn.run(app, host="0.0.0.0", port=8008)

if __name__ == "__main__":
    main()
