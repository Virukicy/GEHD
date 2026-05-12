"""
LLM 后置过滤器 —— 语义深度验证。

v0.4.0-rc: 对 L4 搜索结果做语义级判断——不只判断实体是否存在，
而是判断「文档用这个实体描述的事是否真实」。

仅在 pipeline.llm_post=true + llm 参数非 None 时激活。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import GEHDConfig
    from ..pipeline import PipelineContext
    from .adapter import LLMAdapter


def llm_post_filter(
    context: PipelineContext, llm: LLMAdapter, config: GEHDConfig,
) -> PipelineContext:
    """语义深度验证 — 纠正 Tavily 名称级误判。

    对 verified_real 的 entity，取搜索结果 + 原文上下文，
    LLM 判断实体在行业/业务/性质上是否一致。
    """
    l4_queue: list[dict] = context.get('l4_queue', [])

    corrections: list[dict] = []
    if not l4_queue or llm is None:
        return context

    for entity in l4_queue:
        if entity.get('status') != 'verified_real':
            continue

        word = entity.get('word', '')
        category = entity.get('category', '')
        context_text = entity.get('context', '')
        result = entity.get('search_result', {})
        # 兼容两种字段路径: search_result.snippets 或 entity.snippets
        snippets = result.get('snippets', entity.get('snippets', []))[:3]

        if not snippets or not word:
            continue

        snippet_text = '\n'.join(f'- {s}' for s in snippets)
        messages = [
            {
                'role': 'system',
                'content': (
                    '你是中文幻觉核查专家。搜索结果显示了一个可能存在或名称相似的实体，'
                    '但文档用它描述了一件可能不存在的事。你的任务是：阅读文档上下文和搜索结果，'
                    '判断文档中描述的实体与搜索结果的实体在行业/业务/性质上是否一致。'
                    '返回 JSON: {"consistent": true/false, "reason": "一句话说明"}'
                ),
            },
            {
                'role': 'user',
                'content': (
                    f'实体: 「{word}」（{category}）\n'
                    f'文档上下文: {context_text[:200]}\n'
                    f'搜索结果:\n{snippet_text}'
                ),
            },
        ]

        try:
            reply = llm.chat(messages, temperature=0.0)
            verdict = _safe_parse_json(reply)
        except (json.JSONDecodeError, ValueError):
            try:
                retry = llm.chat([
                    *messages,
                    {'role': 'user', 'content': '请严格只输出 JSON 对象，不要添加任何解释文字、markdown 标记。'},
                ], temperature=0.0)
                verdict = _safe_parse_json(retry)
            except (json.JSONDecodeError, ValueError, OSError):
                continue
        except Exception:
            continue

        if not verdict.get('consistent', True):
            old_status = entity['status']
            entity['status'] = 'verified_fake'
            corrections.append({
                'entity': word,
                'before': old_status,
                'after': 'verified_fake',
                'reason': verdict.get('reason', ''),
            })

    # 若有纠正，重跑 L4 判决反写（升级 issue / 降级 warning）
    if corrections:
        from ..checker import _feedback_l4_verdicts
        issues = context.get('issues', [])
        warnings = context.get('warnings', [])
        stats = context.get('stats', {})
        _feedback_l4_verdicts(l4_queue, issues, warnings, stats, config)

    decision = context.get('decision_log', [])
    decision.append({
        'step': 'llm_post_filter',
        'corrections': corrections,
    })
    context['decision_log'] = decision

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
    return json.loads(text)
