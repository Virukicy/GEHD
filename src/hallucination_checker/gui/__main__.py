"""python -m hallucination_checker.gui 入口。

启动后自动与终端进程脱钩，关闭终端不影响 GUI 窗口。
"""
import os
import sys
from pathlib import Path

# ---- 终端脱钩（macOS） ----
# fork 出子进程运行 GUI，父进程退出释放终端
if sys.platform == 'darwin':
    try:
        pid = os.fork()
        if pid > 0:
            # 父进程：立即退出，终端可关
            sys.exit(0)
        # 子进程：脱离终端进程组
        os.setsid()
        # 重定向标准流到 /dev/null，避免终端残留
        devnull = os.open(os.devnull, os.O_RDWR)
        os.dup2(devnull, 0)
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        os.close(devnull)
    except OSError:
        # fork 失败时继续在原进程运行（不阻塞启动）
        pass

# ---- Qt 插件路径探测 ----
_plugins_dir = Path(sys.executable).parent.parent / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'site-packages' / 'PySide6' / 'Qt' / 'plugins' / 'platforms'
if _plugins_dir.exists() and 'QT_QPA_PLATFORM_PLUGIN_PATH' not in os.environ:
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = str(_plugins_dir)

from hallucination_checker.gui.main_window import main  # noqa: E402

main()
