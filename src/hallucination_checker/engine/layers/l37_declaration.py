"""
L3.7 声明提取层 —— 独立扫描文本中的声明性语言构造（不依赖 L3 实体）。

目标：识别"真实实体 + 虚假事实"类语义幻觉。
策略：直接扫描 all_parts，匹配声明模式，独立产生候选。
"""

from ..config import GEHDConfig


def detect_declarations(
    all_parts: list[tuple[str, str]], config: GEHDConfig
) -> list[dict]:
    """独立扫描文本中的声明性构造。

    与 L2.5 同层级——直接扫描 all_parts，不依赖 L3 候选。
    """
    import re

    candidates: list[dict] = []

    for loc, text in all_parts:
        for pattern, category, base_score in config.declaration_patterns:
            for m in re.finditer(pattern, text):
                try:
                    decl_text = (
                        m.group(1).strip()
                        if m.lastindex and m.lastindex >= 1
                        else m.group().strip()
                    )
                except IndexError:
                    decl_text = m.group().strip()

                if not decl_text or len(decl_text) < 4:
                    continue

                cw = config.context_window_chars * 3
                context = text[max(0, m.start() - cw):m.end() + cw]

                candidates.append({
                    'word': decl_text[:40],
                    'category': f'声明-{category}',
                    'score': base_score,
                    'location': loc,
                    'context': context[:120],
                    'decl_text': decl_text[:80],
                })

    return candidates


def deduplicate_declarations(candidates: list[dict]) -> list[dict]:
    """声明候选去重：同声明文本+同类别保留最高分。"""
    seen: dict[str, dict] = {}
    for ent in candidates:
        key = f'{ent["word"][:20]}|{ent["category"]}'
        if key not in seen or ent['score'] > seen[key]['score']:
            seen[key] = ent

    return sorted(seen.values(), key=lambda x: x['score'], reverse=True)
