"""
L4 联网自动核查 —— 对候选实体执行 Web 搜索验证。

两阶策略:
  - 深度搜索 (score >= deep_search_threshold): 多查询 + 交叉验证
  - 快速搜索 (score <  deep_search_threshold): 单查询 + 首页判断

结果标签:
  - verified_real:    搜索结果确认真实存在
  - verified_fake:    搜索无结果或矛盾 → 疑似幻觉
  - need_manual_check: 信息模糊，需人工判断
  - unable_to_verify:  网络错误或信息不足
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import GEHDConfig


def verify_queue(l4_queue: list[dict], config: GEHDConfig) -> list[dict]:
    """对 L4 候选队列执行联网核查，原地更新状态。

    返回：更新后的 l4_queue（与输入同一个列表对象）。
    """
    for entry in l4_queue:
        word = entry.get('word', '')
        category = entry.get('category', '')
        score = entry.get('score', 0)

        if score >= config.deep_search_threshold:
            status, result = _deep_verify(word, category, config)
        else:
            status, result = _quick_verify(word, category, config)

        entry['status'] = status
        entry['search_result'] = result

    return l4_queue


def get_verification_summary(l4_queue: list[dict]) -> dict:
    """获取验证汇总统计。"""
    return {
        'total': len(l4_queue),
        'verified_real': sum(1 for q in l4_queue if q.get('status') == 'verified_real'),
        'verified_fake': sum(1 for q in l4_queue if q.get('status') == 'verified_fake'),
        'need_manual_check': sum(1 for q in l4_queue if q.get('status') == 'need_manual_check'),
        'unable_to_verify': sum(1 for q in l4_queue if q.get('status') == 'unable_to_verify'),
    }


def get_whitelist_suggestions(l4_queue: list[dict]) -> list[str]:
    """从验证结果提取白名单建议。"""
    return sorted({
        q['word']
        for q in l4_queue
        if q.get('status') == 'verified_real' and q.get('score', 0) < 60
    })


def get_blacklist_suggestions(l4_queue: list[dict]) -> list[str]:
    """从验证结果提取黑名单建议。"""
    return sorted({
        q['word']
        for q in l4_queue
        if q.get('status') == 'verified_fake'
    })


# ---- 搜索实现 ----

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False


def _search_web(query: str, timeout: float = 5) -> list[str]:
    """执行 Web 搜索，返回结果摘要列表。

    使用 DuckDuckGo HTML 搜索（无需 API key）。
    """
    if not _HTTPX_AVAILABLE:
        return []

    try:
        encoded = query.replace(' ', '+')
        url = f'https://html.duckduckgo.com/html/?q={encoded}'

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={
                    'User-Agent': 'GEHD/0.3 (Entity verification bot; research use)',
                },
            )

        if resp.status_code != 200:
            return []

        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL,
        )
        if not snippets:
            snippets = re.findall(
                r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                resp.text,
                re.DOTALL,
            )

        cleaned = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
        return [s for s in cleaned if len(s) > 20]

    except (httpx.HTTPError, OSError, ValueError):
        return []


_ENTITY_INDICATORS = re.compile(
    r'(?:公司|企业|机构|研究院|实验室|大学|学院|平台|集团|中心|基金)'
    r'|(?:宣布|成立|发布|融资|上市|注册|工商)',
)
_NEGATION_INDICATORS = re.compile(
    r'(?:不存在|无法查证|虚构|未注册|无此|查无|不存在于)',
)


def _quick_verify(
    word: str, category: str, config: GEHDConfig | None = None
) -> tuple[str, dict]:
    """快速验证：单次搜索 + 首页判断。"""
    timeout = 5.0 if config is None else getattr(config, 'l4_search_timeout', 5.0)
    query = f'"{word}"'
    snippets = _search_web(query, timeout)

    if not snippets:
        return ('unable_to_verify', {'query': query, 'snippets': [], 'url': '', 'confidence': 0})

    all_text = ' '.join(snippets)
    has_entity = bool(_ENTITY_INDICATORS.search(all_text))
    has_negation = bool(_NEGATION_INDICATORS.search(all_text))

    if has_negation:
        return ('verified_fake', {
            'query': query, 'snippets': snippets[:3], 'url': '',
            'confidence': 0.7,
        })
    elif has_entity and len(snippets) >= 2:
        return ('verified_real', {
            'query': query, 'snippets': snippets[:3], 'url': '',
            'confidence': 0.6,
        })
    else:
        return ('need_manual_check', {
            'query': query, 'snippets': snippets[:3], 'url': '',
            'confidence': 0.3,
        })


def _deep_verify(
    word: str, category: str, config: GEHDConfig | None = None
) -> tuple[str, dict]:
    """深度验证：多查询 + 交叉验证。"""
    timeout = 8.0 if config is None else getattr(config, 'l4_search_timeout', 5.0) + 3

    queries = [
        f'"{word}"',
        f'"{word}" 公司 OR 企业',
        f'"{word}" 成立 OR 注册',
    ]
    all_snippets: list[str] = []
    for q in queries:
        try:
            all_snippets.extend(_search_web(q, timeout / len(queries)))
        except (OSError, RuntimeError):
            continue

    if not all_snippets:
        try:
            all_snippets = _search_web(word, timeout)
        except (OSError, RuntimeError):
            pass
        if not all_snippets:
            return ('unable_to_verify', {
                'query': word, 'snippets': [], 'url': '', 'confidence': 0,
            })

    all_text = ' '.join(all_snippets)
    source_count = len(set(all_snippets[:10]))
    has_entity = bool(_ENTITY_INDICATORS.search(all_text))
    has_negation = bool(_NEGATION_INDICATORS.search(all_text))

    if has_negation:
        return ('verified_fake', {
            'query': word, 'snippets': all_snippets[:5], 'url': '',
            'confidence': 0.85,
        })
    elif has_entity and source_count >= 2:
        return ('verified_real', {
            'query': word, 'snippets': all_snippets[:5], 'url': '',
            'confidence': 0.75,
        })
    elif has_entity:
        return ('need_manual_check', {
            'query': word, 'snippets': all_snippets[:5], 'url': '',
            'confidence': 0.4,
        })
    else:
        return ('verified_fake', {
            'query': word, 'snippets': all_snippets[:5], 'url': '',
            'confidence': 0.5,
        })
