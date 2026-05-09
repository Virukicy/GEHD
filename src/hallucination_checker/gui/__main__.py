"""python -m hallucination_checker.gui 入口。"""
import os
import sys
from pathlib import Path

# 自动探测 PySide6 Qt 插件路径（解决 anaconda/虚拟环境下找不到 cocoa 插件的问题）
_plugins_dir = Path(sys.executable).parent.parent / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'PySide6' / 'Qt' / 'plugins' / 'platforms'
if _plugins_dir.exists() and 'QT_QPA_PLATFORM_PLUGIN_PATH' not in os.environ:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(_plugins_dir)

from hallucination_checker.gui.main_window import main

main()
