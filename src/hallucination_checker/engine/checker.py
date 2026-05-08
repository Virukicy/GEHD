"""
GEHD 主编排器 —— 组合 L1→L4 全链路核查流程。

这是整个引擎的入口，负责按顺序调用各层模块并汇总结果。
外部只需调用 gehd_check(doc, output_verify_queue=False) 即可。
"""

from .layers.l2_blacklist import scan_blacklist
from .layers.l25_nonentity import detect_non_entity, deduplicate_l25
from .layers.l3_heuristic import extract_and_score, deduplicate_entities
from .layers.l36_consistency import run_consistency_checks
from .layers.l4_verify import build_verify_queue
from .extractors.text_extractor import extract_all_text
from .config import (
    SCORE_HIGH_THRESHOLD,
    SCORE_MEDIUM_THRESHOLD,
    L4_STATUS_PENDING,
)


def gehd_check(doc, output_verify_queue: bool = False) -> tuple[list[str], list[str], dict, list[dict]]:
    """GEHD 主核查入口。

    Args:
        doc: python-docx Document 对象
        output_verify_queue: 是否构建 L4 验证队列

    Returns:
        (issues, warnings, stats, l4_verify_queue)
        - issues:   高危问题列表（需立即关注）
        - warnings: 中低危警告列表（待确认）
        - stats:    统计信息 dict
        - l4_verify_queue: L4 待联网核查队列
    """
    issues: list[str] = []
    warnings: list[str] = []
    l4_verify_queue: list[dict] = []

    # 文本提取
    all_parts = extract_all_text(doc)
    full_text = '\n'.join(text for _, text in all_parts)

    # ====== L2: 黑名单拦截 ======
    issues.extend(scan_blacklist(all_parts))

    # ====== L2.5: 非实体幻觉检测 ======
    l25_candidates = detect_non_entity(all_parts)
    l25_ranked = deduplicate_l25(l25_candidates)

    for ent in l25_ranked:
        msg = (
            f'[{ent["category"]}={ent["score"]}] '
            f'{ent["location"]} "{ent["word"]}" '
            f'ctx:"...{ent["context"]}..."'
        )
        if ent['score'] >= SCORE_HIGH_THRESHOLD:
            issues.append(f'[数据-L2.5高危] {msg}')
        elif ent['score'] >= SCORE_MEDIUM_THRESHOLD:
            warnings.append(f'[数据待核实] {msg}')

    # ====== L3: 启发式实体提取 + 评分 ======
    l3_candidates = extract_and_score(all_parts, full_text)
    l3_ranked = deduplicate_entities(l3_candidates)

    # ====== L3.6: 内部一致性检查 ======
    consistency_issues = run_consistency_checks(l3_candidates, all_parts)
    if consistency_issues:
        warnings.append(f'\n  --- L3.6 内部一致性检查 ({len(consistency_issues)}条) ---')
        for ci in consistency_issues:
            loc_str = ci.get('location', '')
            warnings.append(
                f'[一致性-{ci["type"]}] {loc_str} "{ci["word"]}": {ci["detail"]}'
            )

    # 分级输出
    for ent in l3_ranked:
        if ent['score'] >= SCORE_HIGH_THRESHOLD:
            issues.append(
                f'[幻觉-L3高危] {ent["location"]} [{ent["category"]}={ent["score"]}] '
                f'"{ent["word"]}" ctx:"...{ent["context"]}..."'
            )
        elif ent['score'] >= SCORE_MEDIUM_THRESHOLD:
            warnings.append(
                f'[实体待核实] {ent["location"]} [{ent["category"]}={ent["score"]}] '
                f'"{ent["word"]}"'
            )

    # ====== 统计 ======
    high_risk = sum(1 for e in l3_ranked if e['score'] >= SCORE_HIGH_THRESHOLD)
    medium_risk = sum(1 for e in l3_ranked if SCORE_MEDIUM_THRESHOLD <= e['score'] < SCORE_HIGH_THRESHOLD)

    stats = {
        'total_candidates': len(l3_ranked),
        'l25_candidates': len(l25_ranked),
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': len(l3_ranked) - high_risk - medium_risk,
        'l4_queue_size': 0,
    }

    # ====== L4: 验证队列 ======
    if output_verify_queue:
        l4_verify_queue = build_verify_queue(l25_ranked, l3_ranked)
        stats['l4_queue_size'] = len(l4_verify_queue)

    return issues, warnings, stats, l4_verify_queue
