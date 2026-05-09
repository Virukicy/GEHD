"""
P2-5 多模型交叉校验 —— 三路配置并行 + 共识模型。

核心理念：GEHD 是确定性规则引擎，同一文档+同一配置永远产出相同结果。
通过多配置并行实现"交叉校验"效果——不同灵敏度独立检测，交叉比对增强置信度。
"""

from __future__ import annotations

from .config import GEHDConfig


def cross_validate_presets() -> tuple[GEHDConfig, GEHDConfig, GEHDConfig]:
    """返回三套预置配置：默认 / 宽松 / 严格。"""
    config_a = GEHDConfig.default()  # 默认

    config_b = GEHDConfig(
        score_high_threshold=80,
        score_medium_threshold=60,
    )  # 宽松：减少误报

    config_c = GEHDConfig(
        score_high_threshold=50,
        score_medium_threshold=30,
    )  # 严格：扩大覆盖面

    return config_a, config_b, config_c


def gehd_cross_validate(
    document_text,
    output_verify_queue: bool = True,
) -> tuple[list[str], list[str], dict, list[dict]]:
    """三路并行交叉校验。

    对同一文档用三套不同灵敏度配置独立检测，交���比对结果：
      - 三路都出现的实体 → "强共识"
      - 两路出现        → "弱共识"
      - 仅一路出现      → "分歧"

    返回 gehd_check() 兼容的四元组，l4_queue 每个 entity 追加
    cross_validation 字段。

    Args:
        document_text: DocumentText 实例
        output_verify_queue: 是否构建 L4 队列

    Returns:
        (issues, warnings, stats, l4_queue)
    """
    from ..engine.checker import gehd_check

    config_a, config_b, config_c = cross_validate_presets()

    # 三路并行检测
    issues_a, warnings_a, stats_a, queue_a = gehd_check(
        document_text, config_a, output_verify_queue=output_verify_queue
    )
    issues_b, warnings_b, stats_b, queue_b = gehd_check(
        document_text, config_b, output_verify_queue=output_verify_queue
    )
    issues_c, warnings_c, stats_c, queue_c = gehd_check(
        document_text, config_c, output_verify_queue=output_verify_queue
    )

    # 去重合并 issues/warnings（以 A 路为基础，追加 B/C 独有的）
    issues = list(issues_a)
    for iss in issues_b + issues_c:
        if iss not in issues:
            issues.append(iss)

    warnings = list(warnings_a)
    for w in warnings_b + warnings_c:
        if w not in warnings:
            warnings.append(w)

    # 合并 stats
    stats = {
        'cross_validate_mode': True,
        'A_issues': len(issues_a), 'B_issues': len(issues_b), 'C_issues': len(issues_c),
        'A_warnings': len(warnings_a), 'B_warnings': len(warnings_b), 'C_warnings': len(warnings_c),
        'merged_issues': len(issues),
        'merged_warnings': len(warnings),
    }

    # 交叉比对 queue
    cross_queue = _merge_queues(queue_a, queue_b, queue_c)
    stats['cross_high_consensus'] = sum(
        1 for q in cross_queue if q.get('cross_validation', {}).get('consensus_level') == 'strong'
    )
    stats['cross_weak_consensus'] = sum(
        1 for q in cross_queue if q.get('cross_validation', {}).get('consensus_level') == 'weak'
    )
    stats['cross_divergent'] = sum(
        1 for q in cross_queue if q.get('cross_validation', {}).get('consensus_level') == 'divergent'
    )

    return issues, warnings, stats, cross_queue


def _merge_queues(
    queue_a: list[dict], queue_b: list[dict], queue_c: list[dict]
) -> list[dict]:
    """合并三路队列，计算共识级别。"""
    # 构建索引：word → {A: entity, B: entity, C: entity}
    index: dict[str, dict[str, dict]] = {}

    for label, queue in [('A', queue_a), ('B', queue_b), ('C', queue_c)]:
        for entity in queue:
            word = entity.get('word', '')
            index.setdefault(word, {})
            index[word][label] = entity

    merged: list[dict] = []
    for _word, sources in index.items():
        appeared = sorted(sources.keys())
        count = len(appeared)

        if count == 3:
            consensus = 'strong'
        elif count == 2:
            consensus = 'weak'
        else:
            consensus = 'divergent'

        # 以第一出现的路作为主 entity，提取跨路分数和类别
        primary = sources[appeared[0]]
        scores = {k: sources[k].get('score', 0) for k in sources}
        categories = {k: sources[k].get('category', '') for k in sources}

        entity = dict(primary)  # 浅拷贝
        entity['cross_validation'] = {
            'consensus_level': consensus,
            'appeared_in': appeared,
            'scores': scores,
            'categories': categories,
            'disagreement_type': _classify_disagreement(sources),
        }

        # 取最高分为主分数
        entity['score'] = max(scores.values())

        merged.append(entity)

    return sorted(merged, key=lambda x: (
        0 if x.get('cross_validation', {}).get('consensus_level') == 'strong' else
        1 if x.get('cross_validation', {}).get('consensus_level') == 'weak' else 2,
        -x.get('score', 0),
    ))


def _classify_disagreement(sources: dict[str, dict]) -> str:
    """分类分歧类型。"""
    categories = [s['category'] for s in sources.values()]
    if len(set(categories)) > 1:
        return 'category_mismatch'
    scores = [s['score'] for s in sources.values()]
    if max(scores) - min(scores) > 15:
        return 'large_score_gap'
    return 'none'
