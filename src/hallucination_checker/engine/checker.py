"""
GEHD 主编排器 —— 组合 L1→L4 全链路核查流程。

入口（v0.3.0 冻结）:
  gehd_check(text: DocumentText, config, ...) → 主入口
  gehd_check_docx(doc: Document, config, ...) → 向后兼容（v0.4.0 移除）
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.document import Document

from ..io.document_text import DocumentText
from .config import GEHDConfig
from .extractors.text_extractor import extract_all_text
from .layers.l2_blacklist import scan_blacklist
from .layers.l3_heuristic import deduplicate_entities, extract_and_score
from .layers.l4_verify import build_verify_queue
from .layers.l25_nonentity import deduplicate_l25, detect_non_entity
from .layers.l36_consistency import run_consistency_checks


def gehd_check(
    text: DocumentText, config: GEHDConfig, output_verify_queue: bool = False
) -> tuple[list[str], list[str], dict, list[dict]]:
    """GEHD 主核查入口（v0.3.0 冻结签名）。

    Args:
        text: DocumentText — 格式无关的文档表示
        config: GEHDConfig 配置实例
        output_verify_queue: 是否构建 L4 验证队列

    Returns:
        (issues, warnings, stats, l4_verify_queue)
    """
    all_parts = [(p.location, p.text) for p in text.parts]
    return _gehd_check_impl(all_parts, text.full_text, config, output_verify_queue)


def gehd_check_docx(
    doc: Document, config: GEHDConfig, output_verify_queue: bool = False
) -> tuple[list[str], list[str], dict, list[dict]]:
    """【已弃用】从 docx Document 对象执行核查。

    v0.4.0 将移除此函数，请使用 gehd_check(DocumentText, ...)。
    """
    warnings.warn(
        'gehd_check_docx() 已弃用，请使用 gehd_check(DocumentText, ...)',
        DeprecationWarning,
        stacklevel=2,
    )
    all_parts = extract_all_text(doc)
    full_text = '\n'.join(text for _, text in all_parts)
    return _gehd_check_impl(all_parts, full_text, config, output_verify_queue)


# ---- 核心实现（不暴露，两个入口共享） ----


def _gehd_check_impl(
    all_parts: list[tuple[str, str]],
    full_text: str,
    config: GEHDConfig,
    output_verify_queue: bool = False,
) -> tuple[list[str], list[str], dict, list[dict]]:
    """gehd_check 的核心实现——所有入口最终汇入此函数。"""
    issues: list[str] = []
    warnings: list[str] = []
    l4_verify_queue: list[dict] = []

    # L2: 黑名单拦截
    issues.extend(scan_blacklist(all_parts, config))

    # L2.5: 非实体幻觉检测
    l25_candidates = detect_non_entity(all_parts, config)
    l25_ranked = deduplicate_l25(l25_candidates)

    for ent in l25_ranked:
        msg = (
            f'[{ent["category"]}={ent["score"]}] '
            f'{ent["location"]} "{ent["word"]}" '
            f'ctx:"...{ent["context"]}..."'
        )
        if ent['score'] >= config.score_high_threshold:
            issues.append(f'[数据-L2.5高危] {msg}')
        elif ent['score'] >= config.score_medium_threshold:
            warnings.append(f'[数据待核实] {msg}')

    # L3: 启发式实体提取 + 评分
    l3_candidates = extract_and_score(all_parts, full_text, config)
    l3_ranked = deduplicate_entities(l3_candidates)

    # L3.6: 内部一致性检查
    consistency_issues = run_consistency_checks(l3_candidates, all_parts)
    if consistency_issues:
        warnings.append(f'\n  --- L3.6 内部一致性检查 ({len(consistency_issues)}条) ---')
        for ci in consistency_issues:
            loc_str = ci.get('location', '')
            warnings.append(f'[一致性-{ci["type"]}] {loc_str} "{ci["word"]}": {ci["detail"]}')

    # 分级输出
    for ent in l3_ranked:
        if ent['score'] >= config.score_high_threshold:
            issues.append(
                f'[幻觉-L3高危] {ent["location"]} [{ent["category"]}={ent["score"]}] '
                f'"{ent["word"]}" ctx:"...{ent["context"]}..."'
            )
        elif ent['score'] >= config.score_medium_threshold:
            warnings.append(
                f'[实体待核实] {ent["location"]} [{ent["category"]}={ent["score"]}] "{ent["word"]}"'
            )

    # 统计
    high_risk = sum(1 for e in l3_ranked if e['score'] >= config.score_high_threshold)
    medium_risk = sum(
        1
        for e in l3_ranked
        if config.score_medium_threshold <= e['score'] < config.score_high_threshold
    )

    stats = {
        'total_candidates': len(l3_ranked),
        'l25_candidates': len(l25_ranked),
        'high_risk': high_risk,
        'medium_risk': medium_risk,
        'low_risk': len(l3_ranked) - high_risk - medium_risk,
        'l4_queue_size': 0,
    }

    # L4: 验证队列
    if output_verify_queue:
        l4_verify_queue = build_verify_queue(l25_ranked, l3_ranked)
        stats['l4_queue_size'] = len(l4_verify_queue)

    return issues, warnings, stats, l4_verify_queue
