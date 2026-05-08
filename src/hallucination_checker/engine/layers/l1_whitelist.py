"""
L1 白名单放行层 —— 已知真实存在的专有名词直接跳过，不进入后续检测。

策略：
  1. 精确匹配：候选词 == 白名单词 → 直接放行
  2. 子串匹配（收紧）：
     - 2字白名单词 → 必须是候选词前缀（如"华为技术"中的"华为"）
     - 3字+白名单词 → 任意位置子串（如"已在龙旗科技"中的"龙旗科技"）
     - 剩余部分 ≥2字 → 可能是复合名，降分但不放行
     - 剩余部分很短 → 基本就是白名单词，正常放行
"""

from ..config import WHITELIST


def check_whitelist(word: str) -> str | None:
    """检查候选词是否应在白名单中放行。

    Args:
        word: 候选实体词

    Returns:
        None → 放行（跳过后续检测）
        字符串 → 匹配到的白名单词（用于子串白名单的进一步检查）
    """
    # 精确匹配
    if word in WHITELIST:
        return None

    return None  # 精确不匹配，进入子串检查阶段


def check_substring_whitelist(word: str) -> tuple[str | None, bool, str]:
    """子串白名单检查 —— 处理"华为技术有限公司"这类复合名。

    Args:
        word: 候选实体词

    Returns:
        (matched_wl, should_skip, remainder)
        - matched_wl: 匹配到的白名单词（None 表示未匹配）
        - should_skip: True = 完全放行, False = 需要进一步检查
        - remainder: 去除白名单词后的剩余部分
    """
    for wl_word in WHITELIST:
        if len(wl_word) >= 3 and wl_word in word:
            # 3字以上：子串匹配即可
            remainder = word.replace(wl_word, '', 1).strip()
            if len(remainder) < 2:
                return (wl_word, True, remainder)
            else:
                return (wl_word, False, remainder)
        elif len(wl_word) == 2 and word.startswith(wl_word):
            # 2字词：必须是前缀
            remainder = word.replace(wl_word, '', 1).strip()
            if len(remainder) < 2:
                return (wl_word, True, remainder)
            else:
                return (wl_word, False, remainder)

    return (None, False, '')
