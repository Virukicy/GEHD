"""
L3.6 内部一致性检查层 —— 检测文档内部的逻辑矛盾。

两个子检测：
  3.6a: 高频实体检测 —— 同一实体在 ≥3 处出现时标记
  3.6b: 金额矛盾检测 —— 同一段落出现多个金额数字可能矛盾
"""

import re

from ..config import ENTITY_PATTERNS


def check_entity_frequency(candidates: list[dict]) -> list[dict]:
    """3.6a: 统计同一实体的出现频率。

    在 AI 幻觉场景中，虚构的核心概念会在文档中被反复提及，
    高频率本身不是问题，但需要人工关注一致性。

    Args:
        candidates: L3 原始候选列表（去重前）

    Returns:
        一致性 issue 列表
    """
    entity_locations: dict[str, list[dict]] = {}
    for ent in candidates:
        w = ent['word']
        if w not in entity_locations:
            entity_locations[w] = []
        entity_locations[w].append(ent)

    issues: list[dict] = []
    for word, occurrences in entity_locations.items():
        if len(occurrences) >= 3:
            locations_str = ', '.join(o['location'] for o in occurrences[:3])
            issues.append({
                'type': '高频实体',
                'word': word,
                'detail': f'"{word}"出现{len(occurrences)}次 ({locations_str})',
                'locations': [o['location'] for o in occurrences],
            })

    return issues


def check_amount_conflicts(all_parts: list[tuple[str, str]]) -> list[dict]:
    """3.6b: 检测同一段落中的多金额共存。

    同一处出现多个金额数字可能是矛盾或需要交叉验证。

    Args:
        all_parts: [(位置, 文本), ...]

    Returns:
        一致性 issue 列表
    """
    amount_pattern = re.compile(r'(\d+(?:\.\d+)?(?:万亿|亿|万)?(?:元|美元|人民币))')
    issues: list[dict] = []

    for loc, text in all_parts:
        amounts = amount_pattern.findall(text)
        if len(amounts) >= 2:
            issues.append({
                'type': '多金额共存',
                'word': '|'.join(amounts[:3]),
                'detail': f'{loc}同时出现{len(amounts)}个金额数字: {amounts}',
                'location': loc,
            })

    return issues


def run_consistency_checks(candidates: list[dict], all_parts: list[tuple[str, str]]) -> list[dict]:
    """运行所有 L3.6 一致性检查。

    Returns:
        所有一致性 issue 的列表
    """
    issues = check_entity_frequency(candidates)
    issues.extend(check_amount_conflicts(all_parts))
    return issues
