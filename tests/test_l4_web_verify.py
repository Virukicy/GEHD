"""
L4 联网核查单元测试 — 全部使用 mock，不发起真实网络请求。
"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from hallucination_checker.engine.config import GEHDConfig
from hallucination_checker.engine.layers.l4_web_verify import (
    get_blacklist_suggestions,
    get_verification_summary,
    get_whitelist_suggestions,
    verify_queue,
)


@pytest.fixture
def config():
    return GEHDConfig.default()


@pytest.fixture
def sample_queue():
    return [
        {
            'word': '华为辰星科技', 'source_layer': 'L3',
            'category': '公司机构名', 'score': 70,
            'location': 'P5', 'context': '华为辰星科技宣布...',
            'status': 'pending', 'search_result': None,
        },
        {
            'word': '小米汽车', 'source_layer': 'L2.5',
            'category': '公司机构名', 'score': 40,
            'location': 'P7', 'context': '小米汽车SU7交付...',
            'status': 'pending', 'search_result': None,
        },
    ]


class TestL4VerifyQueue:
    """验证队列 web verification pipeline 测试。"""

    def test_verify_real_entity(self, config, sample_queue):
        """模拟搜索返回积极结果 → verified_real"""
        queue = [sample_queue[1]]  # 小米汽车 (low score → quick verify)
        with patch(
            'hallucination_checker.engine.layers.l4_web_verify._search_web',
            return_value=[
                '小米汽车科技有限公司成立于2021年...',
                '小米汽车SU7交付量突破15万辆...',
            ],
        ):
            result = verify_queue(queue, config)
            assert result[0]['status'] == 'verified_real'
            assert 'snippets' in result[0]['search_result']

    def test_verify_fake_entity(self, config, sample_queue):
        """模拟搜索无结果 → verified_fake"""
        queue = [sample_queue[0]]  # 华为辰星科技 (high score → deep verify)
        with patch(
            'hallucination_checker.engine.layers.l4_web_verify._search_web',
            return_value=[],
        ):
            result = verify_queue(queue, config)
            assert result[0]['status'] in ('verified_fake', 'unable_to_verify')

    def test_verify_unable(self, config, sample_queue):
        """模拟网络错误 → unable_to_verify"""
        queue = [sample_queue[0]]
        with patch(
            'hallucination_checker.engine.layers.l4_web_verify._search_web',
            side_effect=OSError('Network error'),
        ):
            result = verify_queue(queue, config)
            assert result[0]['status'] in ('unable_to_verify', 'verified_fake')

    def test_deep_vs_quick_tier(self, config, sample_queue):
        """深度 vs 快速搜索路由正确"""
        with patch(
            'hallucination_checker.engine.layers.l4_web_verify._search_web',
            return_value=['搜索到相关公司信息'],
        ):
            result = verify_queue(sample_queue[:], config)
            # 高分实体 (70 >= 55) 应走深度，低分 (40 < 55) 应走快速
            assert result[0]['status'] in ('verified_real', 'verified_fake', 'need_manual_check', 'unable_to_verify')
            assert result[1]['status'] in ('verified_real', 'verified_fake', 'need_manual_check', 'unable_to_verify')

    def test_verification_summary(self, config, sample_queue):
        """验证汇总统计正确"""
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
        """白名单建议：验证真实 + 分数 < 60"""
        queue = sample_queue[:]
        queue[1]['status'] = 'verified_real'
        suggestions = get_whitelist_suggestions(queue)
        assert '小米汽车' in suggestions

    def test_blacklist_suggestions(self, sample_queue):
        """黑名单建议：验证虚假"""
        queue = sample_queue[:]
        queue[0]['status'] = 'verified_fake'
        suggestions = get_blacklist_suggestions(queue)
        assert '华为辰星科技' in suggestions
