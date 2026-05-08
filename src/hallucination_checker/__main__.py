"""CLI 入口 — 支持 `python -m hallucination_checker <file.docx>` 运行"""

import sys
import os

# 确保 src/ 在 sys.path 中（开发模式下无需安装）
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def main():
    """主入口 — 薄层，委托给 cli/main.py"""
    from hallucination_checker.cli.main import main as cli_main
    cli_main()
