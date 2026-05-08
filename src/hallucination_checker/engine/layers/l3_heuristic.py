"""
L3 启发式实体提取与评分层 —— GEHD 的核心引擎。

流程：
  1. 用 ENTITY_PATTERNS 正则从文本中提取所有候选专有名词
  2. 对每个候选依次检查：
     a. 白名单精确/子串匹配 → 放行或降分
     b. 排除词过滤 → 剔除误报
     c. 形容词前缀检测 → 大幅降分
     d. 频率信号 → 高频词加分（AI 幻觉中虚构概念会被反复提及）
     e. 可信字符 → 特定场景降分
  3. 输出 0-100 分候选列表
"""

import re

from .l1_whitelist import check_substring_whitelist
from ..config import (
    WHITELIST,
    ENTITY_PATTERNS,
    NOISE_PREFIXES,
    EXCLUDE_WORDS,
    ENTITY_SUFFIXES_FOR_EXCLUSION,
    ADJECTIVE_PREFIXES,
    MIN_CANDIDATE_LENGTH,
    CONTEXT_WINDOW_CHARS,
    SCORE_SINGLE_CHAR_PLATFORM,
    SCORE_L35_PENALTY,
    SCORE_HIGH_FREQ_BONUS,
    SCORE_MED_FREQ_BONUS,
    SCORE_PLAUSIBLE_CHAR_PENALTY,
    SCORE_MINIMUM,
)


def extract_and_score(all_parts: list[tuple[str, str]], full_text: str) -> list[dict]:
    """从文本中提取候选实体并评分。

    Args:
        all_parts: [(位置, 文本), ...]
        full_text: 全文（用于频率统计）

    Returns:
        候选实体列表，每项 dict: {word, category, score, location, context}
    """
    candidates: list[dict] = []

    for loc, text in all_parts:
        for pattern, category, base_score in ENTITY_PATTERNS:
            for m in re.finditer(pattern, text):
                # 获取核心实体名（优先用 group(1)）
                try:
                    word = m.group(1).strip() if m.lastindex and m.lastindex >= 1 else m.group().strip()
                except IndexError:
                    word = m.group().strip()

                # 去除中文前置噪音（"在XX" → "XX"）
                while len(word) > 2 and word[0] in NOISE_PREFIXES:
                    word = word[1:]

                if not word or len(word) < MIN_CANDIDATE_LENGTH:
                    continue

                # --- L1: 白名单检查 ---
                if word in WHITELIST:
                    continue

                matched_wl, should_skip, remainder = check_substring_whitelist(word)
                if should_skip:
                    continue
                if matched_wl:
                    # 子串匹配但剩余≥2字 → 降分，不跳过
                    score_penalty = min(15, len(remainder) * 3)
                    base_score = max(30, base_score - score_penalty)

                # --- 排除词过滤 ---
                if _is_excluded(word):
                    continue

                # --- 评分 ---
                score = base_score

                # L3.5: 形容词前缀降分
                for adj in ADJECTIVE_PREFIXES:
                    if word.startswith(adj):
                        score = max(5, score - SCORE_L35_PENALTY)
                        break

                # 单字电商平台加分
                if re.match(r'^[\u4e00-\u9fff]{1}(?:购|宝|东)', word):
                    score += SCORE_SINGLE_CHAR_PLATFORM

                # 频率信号
                count = full_text.count(word)
                if count >= 3:
                    score += SCORE_HIGH_FREQ_BONUS
                elif count >= 2:
                    score += SCORE_MED_FREQ_BONUS

                # 可信字符降分
                plausible_chars = any(c in word for c in ['淘', '京', '拼', '多', '美', '苏', '阿', '腾', '百'])
                if plausible_chars and category in ('电商平台名', '公司机构名'):
                    score += SCORE_PLAUSIBLE_CHAR_PENALTY

                score = max(SCORE_MINIMUM, score)

                candidates.append({
                    'word': word,
                    'category': category,
                    'score': score,
                    'location': loc,
                    'context': text[max(0, m.start() - CONTEXT_WINDOW_CHARS):m.end() + CONTEXT_WINDOW_CHARS],
                })

    return candidates


def deduplicate_entities(candidates: list[dict]) -> list[dict]:
    """实体去重：同词保留最高分，按分数降序排列。

    Args:
        candidates: 原始候选列表

    Returns:
        去重后按分数降序排列的列表
    """
    seen: dict[str, dict] = {}
    for ent in candidates:
        w = ent['word']
        if w in seen:
            if ent['score'] > seen[w]['score']:
                seen[w] = ent
        else:
            seen[w] = ent

    return sorted(seen.values(), key=lambda x: x['score'], reverse=True)


def _is_excluded(word: str) -> bool:
    """检查候选词是否在排除词表中。

    精确匹配 + 安全前缀匹配（只允许 ±1 字符差异，且排除词后不能跟机构后缀）。
    """
    if word in EXCLUDE_WORDS:
        return True

    for ex in EXCLUDE_WORDS:
        if (word.startswith(ex)
                and len(word) <= len(ex) + 1
                and not any(word.endswith(suf) for suf in ENTITY_SUFFIXES_FOR_EXCLUSION)):
            return True

    return False
