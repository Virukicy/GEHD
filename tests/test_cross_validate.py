"""
P2-5 多模型交叉校验单元测试。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile
from pathlib import Path

from hallucination_checker.engine.cross_validate import (
    _classify_disagreement,
    _merge_queues,
    cross_validate_presets,
    gehd_cross_validate,
)
from hallucination_checker.io.document_text import DocumentText


def _make_queue(words, scores, categories):
    """构造 L4 队列。"""
    return [
        {
            'word': w, 'score': s, 'category': c,
            'location': 'P1', 'context': '', 'status': 'pending', 'search_result': None,
        }
        for w, s, c in zip(words, scores, categories, strict=True)
    ]


class TestConsensusModel:
    """共识模型测试。"""

    def test_strong_consensus(self):
        """三路都出现 → strong"""
        qa = _make_queue(['母丑购'], [70], ['电商平台名'])
        qb = _make_queue(['母丑购'], [72], ['电商平台名'])
        qc = _make_queue(['母丑购'], [68], ['公司机构名'])
        merged = _merge_queues(qa, qb, qc)
        assert merged[0]['cross_validation']['consensus_level'] == 'strong'
        assert merged[0]['cross_validation']['appeared_in'] == ['A', 'B', 'C']

    def test_weak_consensus(self):
        """两路出现 → weak"""
        qa = _make_queue(['灵犀购'], [65], ['电商平台名'])
        qb = _make_queue(['灵犀购'], [67], ['电商平台名'])
        qc = _make_queue([], [], [])
        merged = _merge_queues(qa, qb, qc)
        assert merged[0]['cross_validation']['consensus_level'] == 'weak'

    def test_divergent(self):
        """仅一路出现 → divergent"""
        qa = _make_queue(['独有词'], [60], ['测试'])
        merged = _merge_queues(qa, [], [])
        assert merged[0]['cross_validation']['consensus_level'] == 'divergent'

    def test_category_mismatch(self):
        """类别不一致 → category_mismatch"""
        sources = {
            'A': {'category': '电商平台名', 'score': 70},
            'B': {'category': '公司机构名', 'score': 72},
            'C': {'category': '电商平台名', 'score': 68},
        }
        assert _classify_disagreement(sources) == 'category_mismatch'

    def test_score_sorting(self):
        """强共识优先于弱共识，高分优先于低分"""
        qa = _make_queue(['A', 'B'], [60, 70], ['t1', 't2'])
        qb = _make_queue(['A'], [62], ['t1'])
        qc = _make_queue(['A', 'B'], [58, 72], ['t1', 't2'])
        merged = _merge_queues(qa, qb, qc)
        assert merged[0]['word'] == 'A'  # 三路 → 优先
        assert merged[0]['cross_validation']['consensus_level'] == 'strong'


class TestCrossValidateIntegration:
    """交叉校验集成测试。"""

    def test_basic_cross_validate(self):
        """基本交叉校验不抛出异常"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write('母丑购平台倒闭\n清华大学位于北京\n')
            tmp = f.name

        try:
            doc = DocumentText.from_text(tmp)
            issues, warnings, stats, queue = gehd_cross_validate(doc)
            assert isinstance(issues, list)
            assert isinstance(stats, dict)
            assert stats.get('cross_validate_mode') is True
            # 应有交叉校验统计
            assert 'cross_high_consensus' in stats
            assert 'cross_weak_consensus' in stats
            assert 'cross_divergent' in stats
        finally:
            Path(tmp).unlink(missing_ok=True)


class TestPresets:
    """预置配置测试。"""

    def test_presets_distinct(self):
        """三套配置阈值不同"""
        a, b, c = cross_validate_presets()
        assert a.score_high_threshold == 65
        assert b.score_high_threshold == 80
        assert c.score_high_threshold == 50
