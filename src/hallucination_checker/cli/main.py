"""
CLI 主入口 —— 命令行参数解析与流程编排。
"""

import sys

from ..io.docx_reader import load_docx
from ..io.format_checks import (
    check_markdown,
    check_empty_table_rows,
    check_blank_paragraphs,
    check_emoji,
    check_long_text,
)
from ..io.reporter import (
    print_report_header,
    print_issues_and_warnings,
    print_gehd_stats,
    print_l4_summary,
    print_report_footer,
)
from ..engine.checker import gehd_check
from ..engine.layers.l4_verify import export_queue, load_cache
from ..engine.config import load_config, GEHDConfig


def check_docx(filepath: str, do_verify: bool = False, config: GEHDConfig | None = None) -> tuple[bool, list[dict] | None]:
    """对单个 docx 文件执行全部检查。

    Args:
        filepath: docx 文件路径
        do_verify: 是否输出 L4 核查队列
        config: GEHDConfig 配置（None 则自动加载）

    Returns:
        (全部通过?, L4队列|None)
    """
    if config is None:
        config = load_config()

    # 加载文档
    try:
        doc = load_docx(filepath)
    except (FileNotFoundError, ValueError) as e:
        print(f'[ERROR] {e}')
        return False, None

    all_issues: list[str] = []
    all_warnings: list[str] = []

    # Check 1-5: 基础格式检查
    all_issues.extend(check_markdown(doc))
    all_issues.extend(check_empty_table_rows(doc))
    all_issues.extend(check_blank_paragraphs(doc, config))
    all_issues.extend(check_emoji(doc))
    all_warnings.extend(check_long_text(doc, config))

    # GEHD 幻觉核查
    gehd_issues, gehd_warnings, gehd_stats, l4_queue = gehd_check(
        doc, config, output_verify_queue=do_verify
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

    print_report_footer()

    return len(all_issues) == 0, l4_queue if do_verify else None


def main() -> None:
    """CLI 主入口。"""
    if len(sys.argv) < 2:
        print('用法:')
        print('  python -m hallucination_checker <docx文件路径>')
        print('  python -m hallucination_checker <docx文件路径> --verify  # 输出L4核查队列')
        sys.exit(1)

    do_verify = '--verify' in sys.argv
    target = [a for a in sys.argv[1:] if not a.startswith('--')][0]

    config = load_config()
    result = check_docx(target, do_verify=do_verify, config=config)
    ok = result[0] if isinstance(result, tuple) else result
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
