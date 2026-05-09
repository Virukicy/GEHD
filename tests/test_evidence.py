"""
P2-4 证据链生成单元测试。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hallucination_checker.engine.checker import _build_evidence_chain, _recommend_action


class TestRecommendAction:
    """建议动作逻辑测试。"""

    def test_verified_real_low_score(self):
        assert '建议加白名单' in _recommend_action('verified_real', 40)

    def test_verified_real_high_score(self):
        assert '无需处理' in _recommend_action('verified_real', 70)

    def test_verified_fake(self):
        assert '建议加黑名单' in _recommend_action('verified_fake', 50)

    def test_need_manual_check(self):
        assert '人工复核' in _recommend_action('need_manual_check', 30)

    def test_unable_to_verify(self):
        assert '人机协作' in _recommend_action('unable_to_verify', 20)


class TestEvidenceChain:
    """证据链结构完整性测试。"""

    def test_evidence_structure(self):
        """验证 evidence 包含所有必需字段。"""
        l4_queue = [
            {
                'word': '母丑购', 'category': '电商平台名', 'score': 70,
                'location': 'P1', 'context': '...',
                'status': 'verified_fake', 'search_result': {'confidence': 0.85},
            }
        ]
        l3_candidates = [
            {
                'word': '母丑购', 'category': '电商平台名', 'score': 70,
                'location': 'P1', 'context': '...',
                '_scoring': {
                    'base': 60, 'l35_penalty': 0,
                    'platform_bonus': 15, 'freq_bonus': 3,
                    'plausible_penalty': -10,
                },
            }
        ]
        consistency = [
            {'word': '母丑购', 'type': 'high_frequency', 'detail': '出现4次'}
        ]

        _build_evidence_chain(l4_queue, l3_candidates, consistency)

        evidence = l4_queue[0]['evidence']
        assert 'scoring' in evidence
        assert 'consistency' in evidence
        assert 'verification' in evidence
        assert 'recommendation' in evidence
        assert evidence['consistency']['hit'] is True
        assert evidence['consistency']['type'] == 'high_frequency'
        assert '加黑名单' in evidence['recommendation']

    def test_no_consistency_hit(self):
        """无一致性命中时 evidence 仍完整。"""
        l4_queue = [{'word': '小米', 'score': 40, 'status': 'need_manual_check', 'search_result': {}}]
        _build_evidence_chain(l4_queue, [], [])
        assert l4_queue[0]['evidence']['consistency']['hit'] is False
        assert l4_queue[0]['evidence']['consistency']['type'] == 'none'
