"""
L2 黑名单拦截层 —— 历史已确认的幻觉/虚构词汇，直接标记为问题。
"""

from ..config import GEHDConfig


def scan_blacklist(all_parts: list[tuple[str, str]], config: GEHDConfig) -> list[str]:
    """扫描所有文本块，检查是否包含黑名单词汇。"""
    issues: list[str] = []

    for loc, text in all_parts:
        for fake in config.blacklist:
            if fake in text:
                issues.append(
                    f'[幻觉-L2] {loc} 虚构词 "{fake}": "{text[:55]}"'
                )

    return issues
