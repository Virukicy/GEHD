"""
L3 启发式实体提取与评分层 —— GEHD 的核心引擎。
"""

import re

from ..config import GEHDConfig
from .l1_whitelist import check_substring_whitelist


def extract_and_score(
    all_parts: list[tuple[str, str]], full_text: str, config: GEHDConfig
) -> list[dict]:
    """从文本中提取候选实体并评分。"""
    candidates: list[dict] = []

    for loc, text in all_parts:
        for pattern, category, base_score in config.entity_patterns:
            for m in re.finditer(pattern, text):
                # 保存原始 base_score，避免循环内修改污染后续匹配
                score_base = base_score
                try:
                    word = (
                        m.group(1).strip()
                        if m.lastindex and m.lastindex >= 1
                        else m.group().strip()
                    )
                except IndexError:
                    word = m.group().strip()

                # 去除中文前置噪音
                while len(word) > 2 and word[0] in config.noise_prefixes:
                    word = word[1:]

                if not word or len(word) < config.min_candidate_length:
                    continue

                # L1: 白名单检查
                if word in config.whitelist:
                    continue

                matched_wl, should_skip, remainder = check_substring_whitelist(word, config)
                if should_skip:
                    continue
                if matched_wl:
                    score_penalty = min(15, len(remainder) * 3)
                    score_base = max(30, score_base - score_penalty)

                # 排除词过滤
                if _is_excluded(word, config):
                    continue

                # 评分
                score = score_base

                # L3.5: 形容词前缀降分
                for adj in config.adjective_prefixes:
                    if word.startswith(adj):
                        score = max(5, score - config.score_l35_penalty)
                        break

                # 单字电商平台加分
                if re.match(r'^[\u4e00-\u9fff]{1}(?:购|宝|东)', word):
                    score += config.score_single_char_platform

                # 频率信号
                count = full_text.count(word)
                if count >= 3:
                    score += config.score_high_freq_bonus
                elif count >= 2:
                    score += config.score_med_freq_bonus

                # 可信字符降分
                plausible_chars = any(
                    c in word for c in ['淘', '京', '拼', '多', '美', '苏', '阿', '腾', '百']
                )
                if plausible_chars and category in ('电商平台名', '公司机构名'):
                    score += config.score_plausible_char_penalty

                score = max(config.score_minimum, score)

                cw = config.context_window_chars
                candidates.append(
                    {
                        'word': word,
                        'category': category,
                        'score': score,
                        'location': loc,
                        'context': text[max(0, m.start() - cw) : m.end() + cw],
                    }
                )

    return candidates


def deduplicate_entities(candidates: list[dict]) -> list[dict]:
    """实体去重：同词保留最高分，按分数降序排列。"""
    seen: dict[str, dict] = {}
    for ent in candidates:
        w = ent['word']
        if w in seen:
            if ent['score'] > seen[w]['score']:
                seen[w] = ent
        else:
            seen[w] = ent

    return sorted(seen.values(), key=lambda x: x['score'], reverse=True)


def _is_excluded(word: str, config: GEHDConfig) -> bool:
    """检查候选词是否在排除词表中。"""
    if word in config.exclude_words:
        return True

    for ex in config.exclude_words:
        if (
            word.startswith(ex)
            and len(word) <= len(ex) + 1
            and not any(word.endswith(suf) for suf in config.entity_suffixes_for_exclusion)
        ):
            return True

    return False
