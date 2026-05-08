"""
报告生成器 —— 格式化输出核查结果到终端。

负责将 issues / warnings / stats 以人类可读的方式打印出来，
包括 L4 验证队列的可视化展示。
"""

from ..engine.config import (
    GEHD_VERSION,
    GEHD_VERSION_DATE,
    GEHD_VERSION_HASH,
    SCORE_HIGH_THRESHOLD,
    SCORE_MEDIUM_THRESHOLD,
)


def print_report_header(filepath: str, doc) -> None:
    """打印报告头部信息：版本、文件信息、统计。"""
    print('=' * 65)
    print(f'  DOCX 自检报告 v{GEHD_VERSION} (GEHD + L4联网核查)')
    print(f'  版本: {GEHD_VERSION} | 日期: {GEHD_VERSION_DATE} | 标识: {GEHD_VERSION_HASH}')
    print('=' * 65)
    print(f'  文件: {filepath}')
    print(f'  段落: {len(doc.paragraphs)}  |  表格: {len(doc.tables)}')
    print('=' * 65)


def print_issues_and_warnings(issues: list[str], warnings: list[str]) -> None:
    """打印问题和警告列表。"""
    if issues:
        print(f'\n  [!] 发现 {len(issues)} 个问题:')
        for idx, iss in enumerate(issues, 1):
            print(f'    {idx}. {iss}')
    else:
        print('\n  [OK] 所有检查通过!')

    if warnings:
        print(f'\n  [~] {len(warnings)} 个警告:')
        for idx, w in enumerate(warnings, 1):
            print(f'    {idx}. {w}')


def print_gehd_stats(stats: dict) -> None:
    """打印 GEHD 统计信息。"""
    print(f'\n  --- GEHD v{GEHD_VERSION} 统计 ---')
    print(
        f'  [L3] 实体候选: {stats["total_candidates"]}'
        f'  (高危:{stats["high_risk"]} 中危:{stats["medium_risk"]} 低危:{stats["low_risk"]})'
    )
    if stats.get('l25_candidates', 0) > 0:
        print(f'  [L2.5] 数据/引述候选: {stats["l25_candidates"]}')


def print_l4_summary(l4_queue: list[dict], queue_file: str, cached_count: int) -> None:
    """打印 L4 验证队列摘要。"""
    print(f'\n  === L4 联网核查队列 ({len(l4_queue)} 个待验证) ===')

    # 分层策略
    deep_count = sum(1 for q in l4_queue if q['score'] >= 55)
    quick_count = len(l4_queue) - deep_count
    print(f'  [L4分层] 深度搜索({deep_count}个,≥55分) + 快速搜索({quick_count}个,<55分)')
    print(f'  [L4] 验证队列已导出: {queue_file}')

    if cached_count > 0:
        print(f'  [L4缓存] 已加载{cached_count}条历史验证结果')

    # 简要列表
    for idx, item in enumerate(l4_queue, 1):
        mark = ('***' if item['score'] >= SCORE_HIGH_THRESHOLD
                else (' *' if item['score'] >= SCORE_MEDIUM_THRESHOLD else ''))
        tier = '[深]' if item['score'] >= 55 else '[快]'
        print(
            f'    {idx:2d}. [{item["score"]:2d}分]{tier} '
            f'{item["word"]:<20s} ({item["category"]}){mark}'
        )

    print(f'\n  [L4说明] ***=高危 *=中危 其余=低危 | [深]=深度搜索 [快]=快速搜索')
    print(f'  [L4说明] verdict枚举: verified_real / verified_fake / need_manual_check / unable_to_verify')


def print_report_footer() -> None:
    """打印报告尾部声明。"""
    print('=' * 65)
    print(f'  [声明] 本报告仅提供可疑候选列表，不构成最终事实判定。')
    print(f'         所有中危/低危项需经L4联网核查或人工确认后方可采信。')
    print('=' * 65)
