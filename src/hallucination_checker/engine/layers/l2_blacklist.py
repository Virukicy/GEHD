"""
L2 黑名单拦截层 —— 历史已确认的幻觉/虚构词汇，直接标记为问题。

这一层是"已知假货清单"：在之前的核查中已被证实为虚构的词，
再次出现时直接拦截，不需要重新走 L3 评分流程。
"""

from ..config import BLACKLIST


def scan_blacklist(all_parts: list[tuple[str, str]]) -> list[str]:
    """扫描所有文本块，检查是否包含黑名单词汇。

    Args:
        all_parts: [(位置, 文本), ...]

    Returns:
        issues 列表，每条格式: "[幻觉-L2] 位置 虚构词 \"XX\": \"上下文...\""
    """
    issues: list[str] = []

    for loc, text in all_parts:
        for fake in BLACKLIST:
            if fake in text:
                issues.append(
                    f'[幻觉-L2] {loc} 虚构词 \"{fake}\": \"{text[:55]}\"'
                )

    return issues
