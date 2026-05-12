"""
LLM 前置过滤器 —— 批量去噪。

v0.4.0-beta: 将候选实体打包为一次 API 请求，LLM 分拣垃圾/有效实体。
仅在 config.llm_pre_filter=true 且 llm 参数非 None 时激活。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import GEHDConfig
    from ..pipeline import PipelineContext
    from .adapter import LLMAdapter


def llm_pre_filter(
    context: PipelineContext, llm: LLMAdapter, config: GEHDConfig,
) -> PipelineContext:
    """LLM 批量去噪——分拣垃圾实体与有效实体。

    将当前 candidates 打包，请求 LLM 分拣：
      - 保留 → 标记 decision_log
      - 丢弃（垃圾/噪音）→ 同样记录

    context.candidates 更新为仅保留有效实体。
    原始 candidates 追加到 context.decision_log。
    """
    candidates = context.get('candidates', [])
    if not candidates:
        return context

    # 记录原始候选
    context['decision_log'].append({
        'step': 'llm_pre_filter',
        'input_count': len(candidates),
        'input_candidates': [c.get('word', '') for c in candidates],
    })

    # 构建 LLM 请求
    candidate_text = '\n'.join(
        f'{i}. {c.get("word", "")} [{c.get("category", "")}] score={c.get("score", 0)}'
        for i, c in enumerate(candidates, 1)
    )
    messages = [
        {
            'role': 'system',
            'content': (
                '你是中文幻觉核查前置过滤器。从候选实体列表中分拣噪音，保留可能为专有名词的实体。'
                '返回 JSON: {"keep": [索引号], "discard": [索引号]}。\n\n'
                '示例：限公司→discard（公司后缀碎片），华为辰星科技→keep（疑似虚构专名），'
                '共建→discard（常见动词），龙旗科技→keep（真实公司名）。'
            ),
        },
        {
            'role': 'user',
            'content': f'候选实体列表:\n{candidate_text}',
        },
    ]

    try:
        reply = llm.chat(messages, temperature=0.0)
        verdict = _safe_parse_json(reply)
        keep_idx = set(verdict.get('keep', []))
    except (json.JSONDecodeError, ValueError, KeyError, OSError):
        try:
            retry = llm.chat([
                *messages,
                {'role': 'user', 'content': '请严格只输出 JSON 对象，不要添加任何解释文字、markdown 标记。'},
            ], temperature=0.0)
            verdict = _safe_parse_json(retry)
            keep_idx = set(verdict.get('keep', []))
        except (json.JSONDecodeError, ValueError, KeyError, OSError):
            context['decision_log'][-1]['filtered_count'] = len(candidates)
            return context
    except Exception:
        context['decision_log'][-1]['filtered_count'] = len(candidates)
        return context

    # 分拣
    filtered = [candidates[i - 1] for i in keep_idx if 1 <= i <= len(candidates)]
    context['candidates'] = filtered

    context['decision_log'][-1].update({
        'filtered_count': len(filtered),
        'keep_indices': sorted(keep_idx),
    })

    return context


def _safe_parse_json(raw: str) -> dict:
    """清理 LLM 返回文本中的 markdown 包裹，提取纯 JSON。"""
    import json
    import re

    text = raw.strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text)
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end > start:
        text = text[start:end + 1]
    data: dict = json.loads(text)
    return data
