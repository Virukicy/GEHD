"""
L1 白名单放行层 —— 已知真实存在的专有名词直接跳过，不进入后续检测。
"""

from ..config import GEHDConfig

_COMMON_SUFFIXES = frozenset({
    '有限', '股份', '集团', '科技', '技术', '控股',
    '责任', '合伙', '实业', '产业', '投资', '发展',
    '工程', '建设', '咨询', '服务', '贸易', '销售',
    '传媒', '文化', '教育', '医疗', '生物', '制药',
    '能源', '环保', '电子', '信息', '网络', '数据',
    '智能', '软件', '硬件', '系统', '集成',
})


def check_substring_whitelist(word: str, config: GEHDConfig) -> tuple[str | None, bool, str]:
    """子串白名单检查 —— 处理"华为技术有限公司"这类复合名。

    策略：
      - 2字白名单词 → 必须是候选词前缀（如"华为技术"中的"华为"）
      - 3字+白名单词 → 任意位置子串（如"已在龙旗科技"中的"龙旗科技"）
      - 剩余部分 <2字 → 放行
      - 剩余部分仅为常见公司后缀 → 放行（如"华为辰星科技"+"有限"）
      - 剩余部分 ≥2字 且非后缀 → 复合名，降分但不放行

    Returns:
        (matched_wl, should_skip, remainder)
    """
    whitelist = config.whitelist
    for wl_word in whitelist:
        if len(wl_word) >= 3 and wl_word in word:
            remainder = word.replace(wl_word, '', 1).strip()
            if len(remainder) < 2 or remainder in _COMMON_SUFFIXES:
                return (wl_word, True, remainder)
            else:
                return (wl_word, False, remainder)
        elif len(wl_word) == 2 and word.startswith(wl_word):
            remainder = word.replace(wl_word, '', 1).strip()
            if len(remainder) < 2 or remainder in _COMMON_SUFFIXES:
                return (wl_word, True, remainder)
            else:
                return (wl_word, False, remainder)

    return (None, False, '')
