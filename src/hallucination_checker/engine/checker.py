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
from .layers.l37_declaration import deduplicate_declarations, detect_declarations


def gehd_check(
    text: DocumentText, config: GEHDConfig, output_verify_queue: bool = False,
    llm: 'LLMAdapter | None' = None,
) -> tuple[list[str], list[str], dict, list[dict]]:
    """GEHD 主核查入口（v0.4.0-rc 管道路由）。

    Args:
        text: DocumentText — 格式无关的文档表示
        config: GEHDConfig 配置实例
        output_verify_queue: 是否构建 L4 验证队列
        llm: LLMAdapter 实例，None 则纯规则模式

    Returns:
        (issues, warnings, stats, l4_verify_queue)
    """
    from .pipeline import run_pipeline
    ctx = run_pipeline(text, config, llm, output_verify_queue=output_verify_queue)
    return (ctx['issues'], ctx['warnings'], ctx['stats'], ctx['l4_queue'])


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

    # L3.7: 声明提取
    decl_candidates = detect_declarations(all_parts, config)
    decl_ranked = deduplicate_declarations(decl_candidates)

    for ent in decl_ranked:
        msg = (
            f'[{ent["category"]}] '
            f'{ent["location"]} "{ent["word"]}" '
            f'声明:"{ent.get("decl_text", "")}"'
        )
        if ent['score'] >= config.score_high_threshold:
            issues.append(f'[声明-L3.7高危] {msg}')
        elif ent['score'] >= config.score_medium_threshold:
            warnings.append(f'[声明待核实] {msg}')

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

    # L4: 验证队列 + 联网核查
    if output_verify_queue:
        l4_verify_queue = build_verify_queue(l25_ranked, l3_ranked)
        if config.l4_auto_verify:
            from .layers.l4_web_verify import get_verification_summary, verify_queue
            l4_verify_queue = verify_queue(l4_verify_queue, config)
            summary = get_verification_summary(l4_verify_queue)
            stats['l4_verified_real'] = summary['verified_real']
            stats['l4_verified_fake'] = summary['verified_fake']
        stats['l4_queue_size'] = len(l4_verify_queue)

        # L4 判决反写：verified_fake → 升级 issues, verified_real → 降级 warnings
        if config.l4_auto_verify and l4_verify_queue:
            _feedback_l4_verdicts(l4_verify_queue, issues, warnings, stats, config)

        # P2-4: 证据链生成
        _build_evidence_chain(
            l4_verify_queue, l3_candidates, consistency_issues
        )

    return issues, warnings, stats, l4_verify_queue, l3_ranked


def _build_evidence_chain(
    l4_queue: list[dict],
    l3_candidates: list[dict],
    consistency_issues: list[dict],
) -> None:
    """为 L4 队列中的每个 entity 构建证据链（原地追加 evidence 字段）。

    证据链四段：scoring / consistency / verification / recommendation。
    """
    # 构建 L3 candidate 索引：word → _scoring
    scoring_index: dict[str, dict] = {}
    for cand in l3_candidates:
        if '_scoring' in cand:
            scoring_index.setdefault(cand['word'], cand['_scoring'])

    # 构建 L3.6 一致性索引：word → issue
    consistency_index: dict[str, dict] = {}
    for ci in consistency_issues:
        w = ci.get('word', '')
        if w:
            consistency_index[w] = ci

    for entity in l4_queue:
        word = entity.get('word', '')
        scoring = scoring_index.get(word, {})

        verify_status = entity.get('status', 'pending')
        verify_result = entity.get('search_result', {})
        verify_conf = verify_result.get('confidence', 0) if isinstance(verify_result, dict) else 0

        # 一致性
        cons_hit = word in consistency_index
        cons_info = consistency_index.get(word, {})

        # 建议动作
        recommendation = _recommend_action(verify_status, entity.get('score', 0))

        entity['evidence'] = {
            'scoring': scoring,
            'consistency': {
                'hit': cons_hit,
                'type': cons_info.get('type', 'none'),
                'detail': cons_info.get('detail', ''),
            },
            'verification': {
                'status': verify_status,
                'confidence': verify_conf,
            },
            'recommendation': recommendation,
        }


def _recommend_action(verify_status: str, score: int) -> str:
    """根据验证状态和分数生成建议动作。"""
    if verify_status == 'verified_real':
        return '建议加白名单' if score < 60 else '无需处理'
    elif verify_status == 'verified_fake':
        return '建议加黑名单'
    elif verify_status == 'need_manual_check':
        return '建议人工复核'
    elif verify_status == 'unable_to_verify':
        return '建议人机协作验证'
    return '待处理'


def _feedback_l4_verdicts(
    l4_queue: list[dict],
    issues: list[str],
    warnings: list[str],
    stats: dict,
    config,
) -> None:
    """L4 验证结果反写 issues/warnings。

    - verified_fake + score >= medium_threshold → 升级为 issue
    - verified_real → 从 warnings 移除对应实体
    """
    upgraded = 0
    downgraded = 0

    for entity in l4_queue:
        word = entity.get('word', '')
        status = entity.get('status', 'pending')
        score = entity.get('score', 0)

        if status == 'verified_fake' and score >= config.score_medium_threshold:
            location = entity.get('location', '?')
            issues.append(
                f'[L4确认虚构] 「{word}」（{entity.get("category", "")}）'
                f' 位置 {location}，置信度 {entity.get("search_result", {}).get("confidence", 0):.0%}'
            )
            upgraded += 1

        elif status == 'verified_real':
            # 从 warnings 中移除包含该词的条目
            before = len(warnings)
            warnings[:] = [w for w in warnings if word not in w]
            downgraded += before - len(warnings)

    stats['l4_upgraded_to_issue'] = upgraded
    stats['l4_downgraded_from_warning'] = downgraded
