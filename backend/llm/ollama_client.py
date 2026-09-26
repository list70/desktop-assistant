import httpx
import json
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from config import config

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = 'あなたは親切で知的なデスクトップアシスタントです。ユーザーの質問に丁寧に日本語で答えてください。必要に応じてツールを使って情報を取得したり、タスクを実行できます。'

class OllamaClient:
    def __init__(self, endpoint: Optional[str] = None, client: Optional[httpx.AsyncClient] = None):
        self.endpoint = (endpoint or config.ollama_endpoint).rstrip("/")
        self.model = config.llm_model
        self.client = client if client is not None else httpx.AsyncClient(timeout=60.0)
        self.system_prompt = DEFAULT_SYSTEM_PROMPT

    async def list_models(self) -> List[Dict[str, Any]]:
        """Return locally installed Ollama models, suitable for the settings selector."""
        response = await self.client.get(f"{self.endpoint}/api/tags", timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("Ollama returned an invalid model list")

        models = []
        for item in payload["models"]:
            if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"].strip():
                size = item.get("size")
                models.append({"name": item["name"].strip(), "size": size if isinstance(size, int) else None})
        return sorted(models, key=lambda item: item["name"].casefold())

    def set_model(self, model: str):
        self.model = model

    def set_endpoint(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")

    async def aclose(self):
        await self.client.aclose()

    def _prepare_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not messages or messages[0].get("role") != "system":
            return [{"role": "system", "content": self.system_prompt}] + messages
        return messages

    async def chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.endpoint}/api/chat"
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages),
            "stream": False
        }
        if tools:
            payload["tools"] = tools

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Ollama returned an invalid chat response")
            return payload
        except Exception as e:
            logger.error(f"Error during Ollama chat: {e}")
            return {"message": {"content": "申し訳ありません。エラーが発生しました。"}, "error": str(e)}

    async def chat_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        url = f"{self.endpoint}/api/chat"
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages),
            "stream": True
        }

        try:
            async with self.client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
        except Exception as e:
            logger.error(f"Error during Ollama streaming chat: {e}")
            yield "エラーが発生しました。"

    async def check_health(self) -> bool:
        try:
            response = await self.client.get(self.endpoint)
            return response.status_code == 200
        except Exception:
            return False
