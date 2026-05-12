"""
LLM 直接核验阶段 —— fast 路径用。

v0.5.0: 不需要 Tavily，LLM 根据候选词 + 文档原文上下文直接判断可信度。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import GEHDConfig
    from ..pipeline import PipelineContext
    from .adapter import LLMAdapter


def llm_direct_verify(
    context: PipelineContext, llm: LLMAdapter, config: GEHDConfig,
) -> PipelineContext:
    """对 candidates 中的每个候选，LLM 直接判断：
    - consistent (文档描述合理) → 保留
    - suspicious (可疑但无证据) → 标记 warning
    - fabricated (明显虚构) → 标记 issue
    """
    if not llm:
        return context

    batch = context.get('candidates', [])
    if not batch:
        return context

    entry: dict = {
        'step': 'llm_direct_verify',
        'verdicts': [],
        'input_count': len(batch),
    }

    for c in batch:
        word = c.get('word', '')
        context_text = c.get('context', '')[:300]
        if not word:
            continue
        try:
            prompt = (
                '判断以下实体在文档上下文中是否可信。'
                '返回 JSON: {"verdict": "consistent|suspicious|fabricated", "reason": "..."}'
            )
            reply = llm.chat([
                {'role': 'system', 'content': prompt},
                {'role': 'user', 'content': f'实体: {word}\n上下文: {context_text}'},
            ], temperature=0.0)
            verdict_data = _safe_parse_json(reply)
            entry['verdicts'].append({
                'word': word,
                'verdict': verdict_data.get('verdict', 'suspicious'),
                'reason': verdict_data.get('reason', ''),
            })
        except Exception:
            entry['verdicts'].append({
                'word': word,
                'verdict': 'suspicious',
                'reason': 'LLM call failed',
            })

    context.setdefault('decision_log', []).append(entry)
    return context


def _safe_parse_json(raw: str) -> dict:
    """清理 LLM 返回文本中的 markdown 包裹，提取纯 JSON。"""
    import re

    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)
