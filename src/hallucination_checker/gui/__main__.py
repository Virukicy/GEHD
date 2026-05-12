"""python -m hallucination_checker.gui 入口。

启动后自动与终端进程脱钩，关闭终端不影响 GUI 窗口。
"""
import os
import subprocess
import sys
from pathlib import Path

# ---- Qt 插件路径探测（必须在 fork/subprocess 前设置，子进程继承） ----
_plugins_dir = Path(sys.executable).parent.parent / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'PySide6' / 'Qt' / 'plugins' / 'platforms'
if _plugins_dir.exists() and 'QT_QPA_PLATFORM_PLUGIN_PATH' not in os.environ:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(_plugins_dir)

# ---- 终端脱钩（macOS） ----
if sys.platform == 'darwin' and os.environ.get('_GEHD_GUI_CHILD') != '1':
    # 父进程：启动独立子进程运行 GUI，自身退出释放终端
    os.environ['_GEHD_GUI_CHILD'] = '1'
    subprocess.Popen(
        [sys.executable, '-m', 'hallucination_checker.gui'],
        env=os.environ,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    sys.exit(0)

# 子进程：正常执行 GUI 初始化

from hallucination_checker.gui.main_window import main  # noqa: E402

main()
