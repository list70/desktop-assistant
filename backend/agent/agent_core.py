import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from smolagents import OpenAIServerModel, CodeAgent
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
        
        # Using OpenAIServerModel with Ollama endpoint
        self.model = OpenAIServerModel(
            model_id=config.llm_model,
            api_base=f"{config.ollama_endpoint}/v1",
            api_key="ollama" # Dummy key
        )
        self.agent = CodeAgent(tools=self.tools, model=self.model)

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
        try:
            result = self.agent.run(user_input)
            response_text = str(result)
            tool_calls = [] # In a real implementation we would extract this from agent logs
            
            emotion = self._determine_emotion(response_text)
            
            return AgentResponse(
                text=response_text,
                emotion=emotion,
                tool_calls_made=tool_calls
            )
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            # Fallback to direct LLM call
            response = await self.ollama_client.chat([{"role": "user", "content": user_input}])
            text = response.get("message", {}).get("content", "申し訳ありません、処理中にエラーが発生しました。")
            
            return AgentResponse(
                text=text,
                emotion="sad",
                tool_calls_made=[]
            )
