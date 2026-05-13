"""
CLI 主入口 —— 命令行参数解析与流程编排。
"""

import sys

from ..engine.checker import gehd_check
from ..engine.config import GEHDConfig, load_config
from ..engine.layers.l4_verify import export_queue, load_cache
from ..io.document_text import DocumentText
from ..io.docx_reader import load_docx
from ..io.format_checks import (
    check_blank_paragraphs,
    check_emoji,
    check_empty_table_rows,
    check_long_text,
    check_markdown,
)
from ..io.reporter import (
    print_gehd_stats,
    print_issues_and_warnings,
    print_l4_summary,
    print_report_footer,
    print_report_header,
)
from ..logging_setup import get_logger

logger = get_logger(__name__)


def check_docx(
    filepath: str, do_verify: bool = False, config: GEHDConfig | None = None,
    do_audit: bool = False,
) -> tuple[bool, list[dict] | None]:
    """对单个 docx 文件执行全部检查。

    Args:
        filepath: docx 文件路径
        do_verify: 是否输出 L4 核查队列
        do_audit: 是否输出完整决策日志
        config: GEHDConfig 配置（None 则自动加载）

    Returns:
        (全部通过?, L4队列|None)
    """
    if config is None:
        config = load_config()

    # 加载文档
    try:
        doc = load_docx(filepath)
        text = DocumentText.from_docx(filepath)
    except (FileNotFoundError, ValueError) as e:
        logger.error('文档加载失败: %s', e)
        print(f'[ERROR] {e}')
        return False, None

    all_issues: list[str] = []
    all_warnings: list[str] = []

    # Check 1-5: 基础格式检查（docx 专用）
    all_issues.extend(check_markdown(doc))
    all_issues.extend(check_empty_table_rows(doc))
    all_issues.extend(check_blank_paragraphs(doc, config))
    all_issues.extend(check_emoji(doc))
    all_warnings.extend(check_long_text(doc, config))

    # GEHD 幻觉核查（v0.4.0-rc 管道路由）
    from ..engine.llm.adapter import create_llm_adapter_from_config
    llm = create_llm_adapter_from_config()
    gehd_issues, gehd_warnings, gehd_stats, l4_queue = gehd_check(
        text, config, output_verify_queue=do_verify, llm=llm
    )
    all_issues.extend(gehd_issues)
    all_warnings.extend(gehd_warnings)

    # 输出报告
    print_report_header(filepath, doc)
    print_issues_and_warnings(all_issues, all_warnings)
    print_gehd_stats(gehd_stats)

    if do_verify:
        queue_file = export_queue(filepath, l4_queue, config)
        cached_count, _ = load_cache(filepath)
        print_l4_summary(l4_queue, queue_file, cached_count, config)

    if do_audit:
        print_audit_log(gehd_stats)

    print_report_footer()

    ok = len(all_issues) == 0
    logger.info(
        '核查完成: %s, issues=%d, warnings=%d, l4=%d',
        '通过' if ok else '发现问题',
        len(all_issues),
        len(all_warnings),
        len(l4_queue) if do_verify else 0,
    )
    return ok, l4_queue if do_verify else None


def print_audit_log(stats: dict) -> None:
    """输出完整决策日志为格式化 JSON。"""
    import json

    decision_log = stats.get('_decision_log', [])
    print('\n===== AUDIT LOG =====')
    print(json.dumps(decision_log, ensure_ascii=False, indent=2))
    print('===== END AUDIT LOG =====\n')


def main() -> None:
    """CLI 主入口。"""
    if len(sys.argv) < 2:
        print('用法:')
        print('  python -m hallucination_checker <docx文件路径>')
        print('  python -m hallucination_checker <docx文件路径> --verify   # 输出L4核查队列')
        print('  python -m hallucination_checker <docx文件路径> --audit    # 输出完整决策日志')
        sys.exit(1)

    do_verify = '--verify' in sys.argv
    do_audit = '--audit' in sys.argv
    target = [a for a in sys.argv[1:] if not a.startswith('--')][0]

    config = load_config()
    result = check_docx(target, do_verify=do_verify, config=config, do_audit=do_audit)
    ok = result[0] if isinstance(result, tuple) else result
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
