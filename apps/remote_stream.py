import argparse
import time
import asyncio
import numpy as np
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import uvicorn
import io
import wave
from vieneu import Vieneu
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# Global TTS Instance
tts = None

class StreamRequest(BaseModel):
    text: str
    voice_id: Optional[str] = None

@app.on_event("startup")
def load_model():
    global tts
    print("⏳ Connecting to Remote VieNeu LMDeploy Server on port 23333...")
    
    # We use mode='remote' to connect to the Docker container that user started
    try:
        tts = Vieneu(
            mode='remote', 
            api_base='http://localhost:23333/v1', 
            model_name='pnnbao-ump/VieNeu-TTS'
        )
        print("✅ Connected to Remote Server Successfully")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")

def float32_to_pcm16(audio_float):
    audio_int16 = (audio_float * 32767).clip(-32768, 32767).astype(np.int16)
    return audio_int16.tobytes()

@app.get("/stream")
async def stream_audio(text: str, voice_id: str = None):
    def audio_generator():
        header = io.BytesIO()
        with wave.open(header, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(24000)
            wav_file.setnframes(100_000_000) 
        yield header.getvalue()
        
        start = time.time()
        count = 0
        try:
            for chunk in tts.infer_stream(text):
                if count == 0:
                     print(f"⚡ First sound in {time.time() - start:.3f}s")
                count += 1
                yield float32_to_pcm16(chunk)
                time.sleep(0.001) 
                
        except Exception as e:
            print(f"Error during inference: {e}")

    return StreamingResponse(audio_generator(), media_type="audio/wav")

@app.post("/stream")
async def stream_audio_post(req: StreamRequest):
    return await stream_audio(req.text, req.voice_id)

if __name__ == "__main__":
    print("🌍 Starting Remote Streamer on http://0.0.0.0:8008")
    uvicorn.run(app, host="0.0.0.0", port=8008)
