"""
GEHD 日志系统 —— 文件级别的持久化日志。

终端输出仍使用 print()（保持测试兼容），
本模块提供文件日志记录（含时间戳和行号），用于问题追溯。
"""

import logging
from pathlib import Path

_logger: logging.Logger | None = None


def get_logger(name: str = 'gehd') -> logging.Logger:
    """获取 GEHD 日志器（单例）。

    日志写入当前目录的 gehd.log 文件，含时间戳。
    终端输出不受影响。
    """
    global _logger
    if _logger is not None:
        return _logger

    _logger = logging.getLogger(name)
    _logger.setLevel(logging.DEBUG)

    log_file = Path.cwd() / 'gehd.log'
    try:
        file_handler = logging.FileHandler(str(log_file), encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
        )
        _logger.addHandler(file_handler)
    except OSError:
        pass

    return _logger
