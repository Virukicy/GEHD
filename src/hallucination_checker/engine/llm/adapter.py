"""
LLM 适配层 —— 抽象基类 + OpenAI 适配器。

v0.4.0-alpha: 仅定义接口，不参与默认管道。
实际调用留待 v0.5.0。
"""

from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """LLM 适配器抽象基类。"""

    @abstractmethod
    def chat(
        self, messages: list[dict], model: str = '', temperature: float = 0.0
    ) -> str:
        """发送对话请求，返回助手回复文本。"""
        ...


class OpenAIAdapter(LLMAdapter):
    """OpenAI 兼容 API 适配器。"""

    def __init__(self, api_key: str, base_url: str = 'https://api.openai.com/v1'):
        self._api_key = api_key
        self._base_url = base_url.rstrip('/')

    def chat(
        self, messages: list[dict], model: str = 'gpt-4o', temperature: float = 0.0
    ) -> str:
        """调用 OpenAI 兼容聊天接口。"""
        try:
            import httpx
        except ImportError:
            raise ImportError('httpx 是 LLM 调用的必需依赖') from None

        resp = httpx.post(
            f'{self._base_url}/chat/completions',
            headers={
                'Authorization': f'Bearer {self._api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': messages,
                'temperature': temperature,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data: dict = resp.json()
        return str(data['choices'][0]['message']['content'])
