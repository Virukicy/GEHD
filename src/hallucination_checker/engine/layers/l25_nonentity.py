"""
L2.5 非实体幻觉检测层 —— 覆盖统计数据、引述、时间线类幻觉。
"""

import re

from ..config import GEHDConfig


def detect_non_entity(all_parts: list[tuple[str, str]], config: GEHDConfig) -> list[dict]:
    """检测非实体幻觉候选。"""
    candidates: list[dict] = []

    for loc, text in all_parts:
        for pattern, category, base_score in config.l25_patterns:
            for m in re.finditer(pattern, text):
                try:
                    word = (
                        m.group(1).strip()
                        if m.lastindex and m.lastindex >= 1
                        else m.group().strip()
                    )
                except IndexError:
                    word = m.group().strip()

                if not word or len(word) < 2:
                    continue
                if word in config.l25_exclude_phrases:
                    continue

                cw = config.context_window_chars
                context = text[max(0, m.start() - cw) : m.end() + cw]
                candidates.append(
                    {
                        'word': word,
                        'category': category,
                        'score': base_score,
                        'location': loc,
                        'context': context,
                    }
                )

    return candidates


def deduplicate_l25(candidates: list[dict]) -> list[dict]:
    """L2.5 候选去重：同词保留最高分，按分数降序排列。"""
    seen: dict[str, dict] = {}
    for ent in candidates:
        w = ent['word']
        if w not in seen or ent['score'] > seen[w]['score']:
            seen[w] = ent

    return sorted(seen.values(), key=lambda x: x['score'], reverse=True)
