import logging
import json
import base64
import binascii
from urllib.parse import urlsplit
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
    allow_origins=["null", "file://", "file:///"],  # Electron's file:// origin serializes differently across Chromium versions.
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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
    if agent_manager is not None:
        await agent_manager.ollama_client.aclose()

@app.get("/health")
async def health_check():
    return {"status": "ok", "features": ["ollama_model_selection"]}

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
    ollama_endpoint: str | None = None
    llm_model: str | None = None
    whisper_model_size: str | None = None
    tts_voice: str | None = None


@app.get("/ollama/models")
async def list_ollama_models():
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="Assistant services are not ready")
    try:
        return {"models": await agent_manager.ollama_client.list_models()}
    except Exception:
        logger.exception("Failed to get installed Ollama models")
        raise HTTPException(status_code=503, detail="Ollama is unavailable. Start Ollama and refresh the model list.")

@app.post("/config")
async def update_config(update: ConfigUpdate):
    if agent_manager is None:
        raise HTTPException(status_code=503, detail="Assistant services are not ready")

    if update.ollama_endpoint is not None:
        endpoint = update.ollama_endpoint.strip().rstrip("/")
        parsed = urlsplit(endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=422, detail="Ollama endpoint must be a valid HTTP or HTTPS URL")
        try:
            await agent_manager.set_endpoint(endpoint)
        except OSError:
            logger.exception("Failed to save Ollama endpoint")
            raise HTTPException(status_code=500, detail="Could not save the Ollama endpoint")

    if update.llm_model is not None:
        model_name = update.llm_model.strip()
        if not model_name:
            raise HTTPException(status_code=422, detail="Model name cannot be empty")
        try:
            installed_models = await agent_manager.ollama_client.list_models()
        except Exception:
            logger.exception("Could not validate the selected Ollama model")
            raise HTTPException(status_code=503, detail="Ollama is unavailable. Start Ollama and try again.")
        if not any(model["name"] == model_name for model in installed_models):
            raise HTTPException(status_code=400, detail="Choose a model installed in Ollama")
        try:
            await agent_manager.set_model(model_name)
        except OSError:
            logger.exception("Failed to save the selected Ollama model")
            raise HTTPException(status_code=500, detail="Could not save the selected model")

    if update.whisper_model_size is not None:
        if stt is None:
            raise HTTPException(status_code=503, detail="Speech recognition is not ready")
        try:
            stt.set_model_size(update.whisper_model_size)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))

    if update.tts_voice is not None:
        if tts is None:
            raise HTTPException(status_code=503, detail="Speech output is not ready")
        try:
            tts.set_voice(update.tts_voice)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))

    return await get_config()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    if origin and origin not in {"null", "file://", "file:///"}:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    logger.info("WebSocket connection accepted.")
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "content": "Invalid JSON message."})
                continue
            if not isinstance(message, dict):
                await websocket.send_json({"type": "error", "content": "Invalid message format."})
                continue
            
            msg_type = message.get("type")
            
            if msg_type == "text":
                user_text = message.get("content", "")
                if not isinstance(user_text, str) or not user_text.strip():
                    continue
                if len(user_text) > 12000:
                    await websocket.send_json({"type": "error", "content": "Text message is too long."})
                    continue
                    
                await _handle_user_input(websocket, user_text)
                
            elif msg_type == "audio":
                audio_b64 = message.get("data", "")
                if not isinstance(audio_b64, str) or not audio_b64:
                    continue
                if len(audio_b64) > 24_000_000:
                    await websocket.send_json({"type": "error", "content": "Audio message is too large."})
                    continue
                try:
                    audio_bytes = base64.b64decode(audio_b64, validate=True)
                except (binascii.Error, ValueError):
                    await websocket.send_json({"type": "error", "content": "Invalid audio data."})
                    continue
                await websocket.send_json({"type": "thinking", "content": "Transcribing..."})
                
                # Run STT in threadpool
                loop = asyncio.get_running_loop()
                try:
                    transcription = await loop.run_in_executor(None, stt.transcribe, audio_bytes)
                except Exception:
                    logger.exception("Speech recognition failed")
                    await websocket.send_json({"type": "error", "content": "音声認識を開始できませんでした。Whisperの設定を確認してください。"})
                    continue
                
                if transcription:
                    await websocket.send_json({"type": "transcription", "content": transcription})
                    await _handle_user_input(websocket, transcription)
                else:
                    await websocket.send_json({"type": "error", "content": "Could not understand audio."})
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected.")
    except Exception:
        logger.exception("WebSocket request failed")
        try:
            await websocket.send_json({"type": "error", "content": "サーバーでエラーが発生しました。"})
        except Exception:
            pass

async def _handle_user_input(websocket: WebSocket, user_input: str):
    await websocket.send_json({"type": "thinking", "content": "Thinking..."})
    
    # Process with agent
    response = await agent_manager.process_message(user_input)
    
    # Generate TTS with emotion-aware voice
    loop = asyncio.get_running_loop()
    try:
        audio_b64 = await loop.run_in_executor(
            None, tts.synthesize_base64, response.text, response.emotion
        )
    except Exception:
        logger.exception("Speech synthesis failed; sending the text response without audio")
        audio_b64 = ""
    
    await websocket.send_json({
        "type": "response",
        "content": response.text,
        "emotion": response.emotion,
        "audio": audio_b64
    })

if __name__ == "__main__":
    uvicorn.run(app, host=config.server_host, port=config.server_port)
