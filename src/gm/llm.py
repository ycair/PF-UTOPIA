"""LLM Provider 抽象層 — 預留切換 MiniMax / OpenAI / Ollama 的接口。

目前為 stub。實作時只需繼承 LLMProvider 並實作 chat() 方法。
現有的 context.py + tools.py 已可直接使用，不需等 LLM 層完成。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    finish_reason: str = "stop"


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        context: dict = None,
        tools: list[dict] = None,
        history: list[dict] = None,
    ) -> LLMResponse:
        ...


class MiniMaxProvider(LLMProvider):
    """MiniMax API backend (待實作)."""

    def __init__(self, api_key: str, model: str = "MiniMax-M2.7-highspeed"):
        self.api_key = api_key
        self.model = model

    async def chat(self, system_prompt, user_message, context=None, tools=None, history=None):
        raise NotImplementedError("MiniMax provider not yet implemented")


class OllamaProvider(LLMProvider):
    """Ollama 本地 backend (待實作)."""

    def __init__(self, model: str = "qwen2.5:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    async def chat(self, system_prompt, user_message, context=None, tools=None, history=None):
        raise NotImplementedError("Ollama provider not yet implemented")
