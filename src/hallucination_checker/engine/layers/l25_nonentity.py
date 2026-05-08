"""
L2.5 非实体幻觉检测层 —— 覆盖统计数据、引述、时间线类幻觉。

原 GEHD 只能检测专有名词（公司名、人名等），但更危险的幻觉往往是：
  - "公司营收达到 8000 亿元"（数字可能是编的）
  - "张教授表示该技术已落地"（引述可能是假的）
  - "预计 2026 年 Q3 完成"（时间线可能不实）

这一层专门捕获这类"非实体型幻觉"。
"""

import re

from ..config import (
    L25_PATTERNS,
    L25_EXCLUDE_PHRASES,
    CONTEXT_WINDOW_CHARS,
)


def detect_non_entity(all_parts: list[tuple[str, str]]) -> list[dict]:
    """检测非实体幻觉候选。

    Args:
        all_parts: [(位置, 文本), ...]

    Returns:
        候选列表，每项 dict: {word, category, score, location, context}
    """
    candidates: list[dict] = []

    for loc, text in all_parts:
        for pattern, category, base_score in L25_PATTERNS:
            for m in re.finditer(pattern, text):
                try:
                    word = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group().strip()
                except IndexError:
                    word = m.group().strip()

                if not word or len(word) < 2:
                    continue
                if word in L25_EXCLUDE_PHRASES:
                    continue

                context = text[max(0, m.start() - CONTEXT_WINDOW_CHARS):m.end() + CONTEXT_WINDOW_CHARS]
                candidates.append({
                    'word': word,
                    'category': category,
                    'score': base_score,
                    'location': loc,
                    'context': context,
                })

    return candidates


def deduplicate_l25(candidates: list[dict]) -> list[dict]:
    """L2.5 候选去重：同词保留最高分。

    Args:
        candidates: 原始候选列表

    Returns:
        去重后按分数降序排列的列表
    """
    seen: dict[str, dict] = {}
    for ent in candidates:
        w = ent['word']
        if w not in seen or ent['score'] > seen[w]['score']:
            seen[w] = ent

    return sorted(seen.values(), key=lambda x: x['score'], reverse=True)
