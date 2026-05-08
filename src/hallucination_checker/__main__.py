"""CLI 入口 — 支持 `python -m hallucination_checker <file.docx>` 运行

兼容两种运行模式：
  - pip install -e . 安装后：包已在 sys.path，直接导入
  - 开发模式（未安装）：自动添加 src/ 到 sys.path
"""

import os
import sys


def _ensure_import_path() -> None:
    """确保 hallucination_checker 包可导入。

    优先使用已安装的包，仅在没有安装时才添加 src/ 到 sys.path。
    避免 pip install -e . 安装后 sys.path.insert 导致的路径冲突。
    """
    try:
        import hallucination_checker  # noqa: F401

        return  # 包已安装，无需额外操作
    except ImportError:
        pass

    # 开发模式回退：添加 src/ 到 sys.path
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    _src_path = os.path.join(_project_root, 'src')
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)


_ensure_import_path()


def main():
    """主入口 — 薄层，委托给 cli/main.py"""
    from hallucination_checker.cli.main import main as cli_main

    cli_main()


if __name__ == '__main__':
    main()
