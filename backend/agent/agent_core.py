import asyncio
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from smolagents import OpenAIServerModel, ToolCallingAgent
from llm.ollama_client import OllamaClient
from agent.tools.file_tools import ReadFileTool, WriteFileTool, ListDirectoryTool
from agent.tools.web_tools import WebSearchTool
from agent.tools.system_tools import GetCurrentTimeTool, OpenApplicationTool, GetClipboardTool
from config import config

logger = logging.getLogger(__name__)

@dataclass
class AgentResponse:
    text: str
    emotion: str
    tool_calls_made: List[str]

class AgentManager:
    def __init__(self):
        self.ollama_client = OllamaClient()
        self.tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirectoryTool(),
            WebSearchTool(),
            GetCurrentTimeTool(),
            OpenApplicationTool(),
            GetClipboardTool()
        ]
        
        self._model_lock = asyncio.Lock()
        self.model, self.agent = self._build_agent(config.llm_model, config.ollama_endpoint)

    def _build_agent(self, model_id: str, endpoint: str):
        model = OpenAIServerModel(
            model_id=model_id,
            api_base=f"{endpoint.rstrip('/')}/v1",
            api_key="ollama",  # Ollama ignores this placeholder.
        )
        # ToolCallingAgent invokes only registered tools; CodeAgent executes model-written Python.
        return model, ToolCallingAgent(tools=self.tools, model=model)

    async def set_model(self, model_id: str):
        async with self._model_lock:
            model, agent = self._build_agent(model_id, config.ollama_endpoint)
            previous = config.llm_model
            config.llm_model = model_id
            try:
                config.save_user_settings()
            except OSError:
                config.llm_model = previous
                raise
            self.ollama_client.set_model(model_id)
            self.model, self.agent = model, agent

    async def set_endpoint(self, endpoint: str):
        normalized = endpoint.rstrip("/")
        async with self._model_lock:
            model, agent = self._build_agent(config.llm_model, normalized)
            previous = config.ollama_endpoint
            config.ollama_endpoint = normalized
            try:
                config.save_user_settings()
            except OSError:
                config.ollama_endpoint = previous
                raise
            self.ollama_client.set_endpoint(normalized)
            self.model, self.agent = model, agent

    def _determine_emotion(self, text: str) -> str:
        # Simple heuristic for emotion
        text = text.lower()
        if any(w in text for w in ["嬉しい", "楽しい", "笑", "素晴らしい"]):
            return "happy"
        if any(w in text for w in ["悲しい", "申し訳", "ごめん"]):
            return "sad"
        if any(w in text for w in ["驚き", "えっ", "マジ"]):
            return "surprised"
        return "neutral"

    async def process_message(self, user_input: str) -> AgentResponse:
        async with self._model_lock:
            try:
                result = await asyncio.to_thread(self.agent.run, user_input)
                response_text = str(result)
                tool_calls = []  # Tool-call extraction is not exposed by smolagents here.
                emotion = self._determine_emotion(response_text)
                return AgentResponse(text=response_text, emotion=emotion, tool_calls_made=tool_calls)
            except Exception:
                logger.exception("Agent execution failed; falling back to direct Ollama chat")
                response = await self.ollama_client.chat([{"role": "user", "content": user_input}])
                text = response.get("message", {}).get("content", "申し訳ありません、処理中にエラーが発生しました。")
                if response.get("error"):
                    text = "申し訳ありません。Ollamaへの接続またはモデルの実行に失敗しました。設定からモデルを確認してください。"
                return AgentResponse(text=text, emotion="sad", tool_calls_made=[])
