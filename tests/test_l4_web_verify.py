"""
L4 联网核查单元测试 — 全部使用 mock backend，不发起真实网络请求。
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from hallucination_checker.engine.config import GEHDConfig
from hallucination_checker.engine.layers.l4_web_verify import (
    DuckDuckGoBackend,
    SearchAdapter,
    TavilyBackend,
    _get_search_backend,
    get_blacklist_suggestions,
    get_verification_summary,
    get_whitelist_suggestions,
    verify_queue,
)


@pytest.fixture
def config():
    cfg = GEHDConfig.default()
    object.__setattr__(cfg, 'l4_search_provider', 'duckduckgo')
    return cfg


@pytest.fixture
def sample_queue():
    return [
        {
            'word': '华为辰星科技', 'source_layer': 'L3',
            'category': '公司机构名', 'score': 70,
            'location': 'P5', 'context': '...',
            'status': 'pending', 'search_result': None,
        },
        {
            'word': '小米汽车', 'source_layer': 'L2.5',
            'category': '公司机构名', 'score': 40,
            'location': 'P7', 'context': '...',
            'status': 'pending', 'search_result': None,
        },
    ]


class _MockBackend(SearchAdapter):
    """可配置返回值的测试后端。"""
    def __init__(self, returns=None):
        self.returns = returns or []
        self.calls: list[str] = []

    def search(self, query: str, timeout: float = 5) -> list[str]:
        self.calls.append(query)
        return self.returns


class TestL4VerifyQueue:
    """验证队列 pipeline 测试。"""

    def test_verify_real_entity(self, config, sample_queue):
        backend = _MockBackend([
            '小米汽车科技有限公司成立于2021年...',
            '小米汽车SU7交付量突破15万辆...',
        ])
        queue = [sample_queue[1]]
        with patch('hallucination_checker.engine.layers.l4_web_verify._get_search_backend', return_value=backend):
            result = verify_queue(queue, config)
            assert result[0]['status'] == 'verified_real'
            assert 'snippets' in result[0]['search_result']

    def test_verify_no_backend(self, config, sample_queue):
        with patch('hallucination_checker.engine.layers.l4_web_verify._get_search_backend', return_value=None):
            result = verify_queue(sample_queue[:], config)
            assert result[0]['status'] == 'unable_to_verify'

    def test_deep_vs_quick_tier(self, config, sample_queue):
        backend = _MockBackend(['搜索到相关公司信息'])
        with patch('hallucination_checker.engine.layers.l4_web_verify._get_search_backend', return_value=backend):
            result = verify_queue(sample_queue[:], config)
            assert all(q['status'] in (
                'verified_real', 'verified_fake', 'need_manual_check', 'unable_to_verify',
            ) for q in result)

    def test_verification_summary(self, config, sample_queue):
        queue = sample_queue[:]
        queue[0]['status'] = 'verified_fake'
        queue[0]['search_result'] = {}
        queue[1]['status'] = 'verified_real'
        queue[1]['search_result'] = {}
        summary = get_verification_summary(queue)
        assert summary['total'] == 2
        assert summary['verified_real'] == 1
        assert summary['verified_fake'] == 1

    def test_whitelist_suggestions(self, sample_queue):
        queue = sample_queue[:]
        queue[1]['status'] = 'verified_real'
        suggestions = get_whitelist_suggestions(queue)
        assert '小米汽车' in suggestions

    def test_blacklist_suggestions(self, sample_queue):
        queue = sample_queue[:]
        queue[0]['status'] = 'verified_fake'
        suggestions = get_blacklist_suggestions(queue)
        assert '华为辰星科技' in suggestions


class TestSearchAdapters:
    """搜索后端测试。"""

    def test_duckduckgo_backend_exists(self):
        backend = DuckDuckGoBackend()
        assert isinstance(backend, SearchAdapter)

    def test_tavily_invalid_key(self):
        with pytest.raises(ValueError):
            TavilyBackend('bad-key')

    def test_tavily_valid_key(self):
        backend = TavilyBackend('tvly-dev-test123')
        assert isinstance(backend, SearchAdapter)

    def test_get_backend_auto_tavily(self):
        cfg = GEHDConfig.default()
        object.__setattr__(cfg, 'l4_search_provider', 'auto')
        object.__setattr__(cfg, 'l4_tavily_api_key', 'tvly-dev-test123')
        with patch.object(TavilyBackend, '__init__', return_value=None):
            backend = _get_search_backend(cfg)
            assert isinstance(backend, TavilyBackend)

    def test_get_backend_no_key_falls_to_duckduckgo(self):
        cfg = GEHDConfig.default()
        object.__setattr__(cfg, 'l4_search_provider', 'auto')
        object.__setattr__(cfg, 'l4_tavily_api_key', '')
        backend = _get_search_backend(cfg)
        assert isinstance(backend, DuckDuckGoBackend)


class TestL4FeedbackVerdicts:
    """L4 判决反写逻辑测试。"""

    def test_verified_fake_upgrades_issue(self):
        from hallucination_checker.engine.checker import _feedback_l4_verdicts

        l4_queue = [
            {
                'word': '母丑购', 'category': '电商平台名', 'score': 65,
                'location': 'P1', 'status': 'verified_fake',
                'search_result': {'confidence': 0.85},
            },
        ]
        issues: list[str] = []
        warnings: list[str] = ['[L3-中危] 母丑购 - 电商平台名 (70分)']
        stats: dict = {}
        cfg = GEHDConfig.default()

        _feedback_l4_verdicts(l4_queue, issues, warnings, stats, cfg)

        assert len(issues) >= 1
        assert '母丑购' in issues[0]
        assert stats['l4_upgraded_to_issue'] == 1

    def test_verified_real_downgrades_warning(self):
        from hallucination_checker.engine.checker import _feedback_l4_verdicts

        l4_queue = [
            {
                'word': '小米汽车', 'category': '公司机构名', 'score': 40,
                'location': 'P3', 'status': 'verified_real',
                'search_result': {'confidence': 0.75},
            },
        ]
        issues: list[str] = []
        warnings: list[str] = ['[L3-中危] 小米汽车 - 公司机构名 (40分)']
        stats: dict = {}
        cfg = GEHDConfig.default()

        _feedback_l4_verdicts(l4_queue, issues, warnings, stats, cfg)

        assert len(warnings) == 0
        assert stats['l4_downgraded_from_warning'] == 1
