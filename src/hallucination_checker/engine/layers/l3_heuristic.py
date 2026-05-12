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
                l35_penalty = 0
                platform_bonus = 0
                freq_bonus = 0
                plaus_penalty = 0

                # L3.5: 形容词前缀降分
                for adj in config.adjective_prefixes:
                    if word.startswith(adj):
                        l35_penalty = -config.score_l35_penalty
                        score = max(5, score + l35_penalty)
                        break

                # 单字平台加分（后缀列表来自 config）
                if any(
                    re.match(rf'^[\u4e00-\u9fff]{{1}}(?:{re.escape(s)})', word)
                    for s in config.single_char_platform_suffixes
                ):
                    platform_bonus = config.score_single_char_platform
                    score += platform_bonus

                # 频率信号
                count = full_text.count(word)
                if count >= 3:
                    freq_bonus = config.score_high_freq_bonus
                    score += freq_bonus
                elif count >= 2:
                    freq_bonus = config.score_med_freq_bonus
                    score += freq_bonus

                # 可信字符降分（字符列表和生效类别来自 config）
                plausible_chars = any(
                    c in word for c in config.plausible_chars
                )
                if plausible_chars and category in config.plausible_char_categories:
                    plaus_penalty = config.score_plausible_char_penalty
                    score += plaus_penalty

                # P2-6-A: 子串绕过实体评分加权
                # 如"华为辰星科技"——含真实品牌前缀+虚构后缀
                substr_bonus = 0
                for brand in config.whitelist:
                    if len(brand) >= 2 and len(word) > len(brand) and word.startswith(brand):
                        substr_bonus = 15
                        break
                score += substr_bonus

                final_score = max(config.score_minimum, score)

                cw = config.context_window_chars
                candidates.append(
                    {
                        'word': word,
                        'category': category,
                        'score': final_score,
                        'location': loc,
                        'context': text[max(0, m.start() - cw) : m.end() + cw],
                        '_scoring': {
                            'base': score_base,
                            'l35_penalty': l35_penalty,
                            'platform_bonus': platform_bonus,
                            'freq_bonus': freq_bonus,
                            'plausible_penalty': plaus_penalty,
                            'substr_bonus': substr_bonus,
                        },
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
