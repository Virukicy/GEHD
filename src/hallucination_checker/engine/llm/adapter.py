"""
LLM 适配层 —— 抽象基类 + OpenAI 适配器 + 工厂函数。

v0.4.0-rc: CLI/GUI 共享 create_llm_adapter_from_config()。
"""

from abc import ABC, abstractmethod
from pathlib import Path
import json


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


def create_llm_adapter_from_config() -> OpenAIAdapter | None:
    """根据 pipeline.json / llm.json / secrets.json 创建 LLM 适配器。

    CLI 与 GUI 共享此入口。
    仅在 pipeline.llm_pre 或 llm_post 为 true 时创建。
    """
    from ..config import _find_config_dir

    cfg_dir = _find_config_dir()
    if cfg_dir is None:
        return None

    # 管道开关
    pipeline_cfg = _load_json(cfg_dir / 'pipeline.json')
    steps = pipeline_cfg.get('steps', {})
    if not (steps.get('llm_pre') or steps.get('llm_post')):
        return None

    # LLM 配置
    llm_cfg = _load_json(cfg_dir / 'llm.json')
    secrets = _load_json(cfg_dir / 'secrets.json')
    api_key = secrets.get('llm_api_key', '')
    if not api_key:
        return None

    base_url = llm_cfg.get('base_url', 'https://api.openai.com/v1')
    return OpenAIAdapter(api_key=api_key, base_url=base_url)


def _load_json(path: Path) -> dict:
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
