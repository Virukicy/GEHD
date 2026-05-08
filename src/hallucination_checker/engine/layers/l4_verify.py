"""
L4 联网核查队列构建层 —— 生成待验证候选的 JSON 协议。
"""

import json
import os
from datetime import datetime

from ..config import (
    GEHD_VERSION,
    L4_CACHE_SUFFIX,
    L4_QUEUE_SUFFIX,
    L4_STATUS_PENDING,
    L4_VERDICT_FAKE,
    L4_VERDICT_MANUAL,
    L4_VERDICT_REAL,
    L4_VERDICT_UNABLE,
    GEHDConfig,
)


def build_verify_queue(l25_ranked: list[dict], l3_ranked: list[dict]) -> list[dict]:
    """构建 L4 待验证队列。"""
    queue: list[dict] = []

    for ent in l25_ranked:
        queue.append(
            {
                'word': ent['word'],
                'source_layer': 'L2.5',
                'category': ent['category'],
                'score': ent['score'],
                'location': ent['location'],
                'context': ent['context'],
                'status': L4_STATUS_PENDING,
                'search_result': None,
            }
        )

    for ent in l3_ranked:
        queue.append(
            {
                'word': ent['word'],
                'source_layer': 'L3',
                'category': ent['category'],
                'score': ent['score'],
                'location': ent['location'],
                'context': ent['context'],
                'status': L4_STATUS_PENDING,
                'search_result': None,
            }
        )

    return queue


def export_queue(filepath: str, l4_queue: list[dict], config: GEHDConfig) -> str:
    """导出 L4 验证队列为 JSON 文件。"""
    dst = config.deep_search_threshold
    l4_protocol = {
        'protocol_version': '1.0',
        'gehd_version': GEHD_VERSION,
        'generated_at': datetime.now().isoformat(),
        'source_file': filepath,
        'total_pending': len(l4_queue),
        'tiered_strategy': {
            'deep_search': {
                'condition': f'score >= {dst}',
                'count': sum(1 for q in l4_queue if q['score'] >= dst),
                'method': '多引擎交叉验证 + 来源追溯',
            },
            'quick_search': {
                'condition': f'score < {dst}',
                'count': sum(1 for q in l4_queue if q['score'] < dst),
                'method': '单引擎快速判断 + 首页验证',
            },
        },
        'entities': l4_queue,
        '_verdict_schema': {
            L4_VERDICT_REAL: '已确认真实存在',
            L4_VERDICT_FAKE: '已确认为虚构/幻觉',
            L4_VERDICT_MANUAL: '自动无法判定，需人工核查',
            L4_VERDICT_UNABLE: '信息不足，无法验证',
        },
    }

    queue_file = filepath.replace('.docx', L4_QUEUE_SUFFIX)
    with open(queue_file, 'w', encoding='utf-8') as f:
        json.dump(l4_protocol, f, ensure_ascii=False, indent=2)

    return queue_file


def load_cache(filepath: str) -> tuple[int, list[dict]]:
    """加载已有的 L4 缓存。"""
    cache_file = filepath.replace('.docx', L4_CACHE_SUFFIX)
    if not os.path.exists(cache_file):
        return 0, []

    try:
        with open(cache_file, encoding='utf-8') as f:
            cache = json.load(f)
        verified = cache.get('verified_entities', [])
        return len(verified), verified
    except Exception:
        return 0, []
