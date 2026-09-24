import logging
import json
import base64
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio

from config import config
from stt.whisper_stt import WhisperSTT
from tts.kokoro_tts import KokoroTTS
from agent.agent_core import AgentManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Desktop Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
stt: WhisperSTT = None
tts: KokoroTTS = None
agent_manager: AgentManager = None

@app.on_event("startup")
async def startup_event():
    global stt, tts, agent_manager
    logger.info("Initializing services...")
    stt = WhisperSTT()
    tts = KokoroTTS()
    agent_manager = AgentManager()
    logger.info("Services initialized.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down services...")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/config")
async def get_config():
    return {
        "ollama_endpoint": config.ollama_endpoint,
        "llm_model": config.llm_model,
        "whisper_model_size": config.whisper_model_size,
        "tts_voice": config.tts_voice,
        "server_host": config.server_host,
        "server_port": config.server_port,
    }

class ConfigUpdate(BaseModel):
    ollama_endpoint: str = None
    llm_model: str = None
    whisper_model_size: str = None
    tts_voice: str = None

@app.post("/config")
async def update_config(update: ConfigUpdate):
    if update.ollama_endpoint: config.ollama_endpoint = update.ollama_endpoint
    if update.llm_model: config.llm_model = update.llm_model
    if update.whisper_model_size: config.whisper_model_size = update.whisper_model_size
    if update.tts_voice: config.tts_voice = update.tts_voice
    return {"status": "success", "message": "Configuration updated"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted.")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            
            if msg_type == "text":
                user_text = message.get("content", "")
                if not user_text:
                    continue
                    
                await _handle_user_input(websocket, user_text)
                
            elif msg_type == "audio":
                audio_b64 = message.get("data", "")
                if not audio_b64:
                    continue
                
                audio_bytes = base64.b64decode(audio_b64)
                await websocket.send_json({"type": "thinking", "content": "Transcribing..."})
                
                # Run STT in threadpool
                loop = asyncio.get_event_loop()
                transcription = await loop.run_in_executor(None, stt.transcribe, audio_bytes)
                
                if transcription:
                    await websocket.send_json({"type": "transcription", "content": transcription})
                    await _handle_user_input(websocket, transcription)
                else:
                    await websocket.send_json({"type": "error", "content": "Could not understand audio."})
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass

async def _handle_user_input(websocket: WebSocket, user_input: str):
    await websocket.send_json({"type": "thinking", "content": "Thinking..."})
    
    # Process with agent
    response = await agent_manager.process_message(user_input)
    
    # Generate TTS with emotion-aware voice
    loop = asyncio.get_event_loop()
    audio_b64 = await loop.run_in_executor(
        None, tts.synthesize_base64, response.text, response.emotion
    )
    
    await websocket.send_json({
        "type": "response",
        "content": response.text,
        "emotion": response.emotion,
        "audio": audio_b64
    })

if __name__ == "__main__":
    uvicorn.run(app, host=config.server_host, port=config.server_port)
