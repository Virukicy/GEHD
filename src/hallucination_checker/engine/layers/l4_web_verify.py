"""
L4 联网自动核查 —— 对候选实体执行 Web 搜索验证。

搜索后端:
  - TavilyBackend:    Tavily Search API (优先, 需 API Key)
  - DuckDuckGoBackend: DuckDuckGo HTML 抓取 (回退, 免 Key)

两阶策略:
  - 深度搜索 (score >= deep_search_threshold): 多查询 + 交叉验证
  - 快速搜索 (score <  deep_search_threshold): 单查询 + 首页判断
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ..search.adapter import SearchAdapter

if TYPE_CHECKING:
    from ..config import GEHDConfig

_ENTITY_INDICATORS = re.compile(
    r'(?:公司|企业|机构|研究院|实验室|大学|学院|平台|集团|中心|基金)'
    r'|(?:宣布|成立|发布|融资|上市|注册|工商)',
)
_NEGATION_INDICATORS = re.compile(
    r'(?:不存在|无法查证|虚构|未注册|无此|查无|不存在于)',
)


# ---- DuckDuckGo 后端 ----

class DuckDuckGoBackend(SearchAdapter):
    """DuckDuckGo HTML 搜索（免 API Key）。"""

    def search(self, query: str, timeout: float = 5) -> list[str]:
        try:
            import httpx
        except ImportError:
            return []

        try:
            encoded = query.replace(' ', '+')
            url = f'https://html.duckduckgo.com/html/?q={encoded}'
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(
                    url,
                    headers={'User-Agent': 'GEHD/0.3 (Entity verification bot; research use)'},
                )
            if resp.status_code != 200:
                return []
            snippets = re.findall(
                r'class="result__snippet"[^>]*>(.*?)</a>',
                resp.text, re.DOTALL,
            )
            if not snippets:
                snippets = re.findall(
                    r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
                    resp.text, re.DOTALL,
                )
            cleaned = [re.sub(r'<[^>]+>', '', s).strip() for s in snippets]
            return [s for s in cleaned if len(s) > 20]
        except (OSError, RuntimeError, ValueError):
            return []


# ---- Tavily 后端 ----

class TavilyBackend(SearchAdapter):
    """Tavily Search API 后端（需 API Key）。"""

    def __init__(self, api_key: str):
        if not api_key or not api_key.startswith('tvly-'):
            raise ValueError(f'Tavily API Key 格式异常: {api_key[:4]}...')
        self._api_key = api_key

    def search(self, query: str, timeout: float = 5) -> list[str]:
        try:
            from tavily import TavilyClient
        except ImportError:
            return []

        try:
            client = TavilyClient(api_key=self._api_key)
            response = client.search(
                query=query,
                search_depth='basic',
                max_results=5,
            )
            if not response or 'results' not in response:
                return []
            return [
                r.get('content', r.get('title', ''))
                for r in response['results']
                if r.get('content') or r.get('title')
            ]
        except Exception:
            return []


# ---- 后端工厂 ----

def _get_search_backend(config: GEHDConfig) -> SearchAdapter | None:
    """根据配置选择搜索后端。

    优先级:
      1. Tavily (API Key 存在且 search_provider != 'duckduckgo')
      2. DuckDuckGo (回退)
      3. None (降级为 unable_to_verify)
    """
    provider = config.l4_search_provider

    # 尝试 Tavily
    if provider in ('auto', 'tavily') and config.l4_tavily_api_key:
        try:
            return TavilyBackend(config.l4_tavily_api_key)
        except ValueError:
            pass

    # DuckDuckGo
    if provider in ('auto', 'duckduckgo'):
        return DuckDuckGoBackend()

    return None


# ---- 验证流水线 ----

def verify_queue(l4_queue: list[dict], config: GEHDConfig) -> list[dict]:
    """对 L4 候选队列执行联网核查，原地更新状态。"""
    backend = _get_search_backend(config)
    if backend is None:
        for entry in l4_queue:
            entry['status'] = 'unable_to_verify'
            entry['search_result'] = {
                'query': entry.get('word', ''), 'snippets': [], 'url': '', 'confidence': 0,
            }
        return l4_queue

    for entry in l4_queue:
        word = entry.get('word', '')
        category = entry.get('category', '')
        score = entry.get('score', 0)

        if score >= config.deep_search_threshold:
            status, result = _deep_verify(word, category, config, backend)
        else:
            status, result = _quick_verify(word, category, config, backend)

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
    return sorted({
        q['word'] for q in l4_queue
        if q.get('status') == 'verified_real' and q.get('score', 0) < 60
    })


def get_blacklist_suggestions(l4_queue: list[dict]) -> list[str]:
    return sorted({
        q['word'] for q in l4_queue
        if q.get('status') == 'verified_fake'
    })


def _quick_verify(
    word: str, category: str, config: GEHDConfig, backend: SearchAdapter,
) -> tuple[str, dict]:
    timeout = getattr(config, 'l4_search_timeout', 5.0)
    query = f'"{word}"'
    snippets = backend.search(query, timeout)

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
    word: str, category: str, config: GEHDConfig, backend: SearchAdapter,
) -> tuple[str, dict]:
    timeout = getattr(config, 'l4_search_timeout', 5.0) + 3

    queries = [
        f'"{word}"',
        f'"{word}" 公司 OR 企业',
        f'"{word}" 成立 OR 注册',
    ]
    all_snippets: list[str] = []
    for q in queries:
        try:
            all_snippets.extend(backend.search(q, timeout / len(queries)))
        except (OSError, RuntimeError):
            continue

    if not all_snippets:
        try:
            all_snippets = backend.search(word, timeout)
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
