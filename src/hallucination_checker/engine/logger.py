"""GEHD 日志系统 — 管道、适配器、CLI/GUI 共用。

v0.5.0: scan 存档 + 阶段耗时日志 + LLM/Tavily 调用追踪。
绝不记录 API Key 或 prompt 原文。
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path

LOG_FILE = Path(__file__).resolve().parents[3] / 'gehd.log'
SCAN_DIR = Path(__file__).resolve().parents[3] / 'workspace' / 'scans'


def setup_gehd_logger(name: str = 'gehd') -> logging.Logger:
    """获取或创建 GEHD 命名 logger——文件写入 gehd.log。"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    fh = logging.FileHandler(LOG_FILE, encoding='utf-8')
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger


def save_scan_archive(
    scan_id: str, context: dict, config_snapshot: dict,
) -> Path:
    """归档一次扫描的完整决策上下文到 workspace/scans/<scan_id>.json。"""
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    path = SCAN_DIR / f'{scan_id}.json'
    payload = {
        'scan_id': scan_id,
        'timestamp': datetime.datetime.now().isoformat(),
        'decision_log': context.get('decision_log', []),
        'stats': context.get('stats', {}),
        'issues_count': len(context.get('issues', [])),
        'warnings_count': len(context.get('warnings', [])),
        'config': {
            'mode': config_snapshot.get('mode', ''),
            'model': config_snapshot.get('model', ''),
            'provider': config_snapshot.get('provider', ''),
        },
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
