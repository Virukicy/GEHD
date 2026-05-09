"""
L3.7 声明提取单元测试 — 不依赖外部 docx 文件。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest

from hallucination_checker.engine.config import GEHDConfig
from hallucination_checker.engine.layers.l37_declaration import (
    deduplicate_declarations,
    detect_declarations,
)


@pytest.fixture
def config():
    return GEHDConfig.default()


class TestDeclarationDetection:
    """声明提取核心检测测试。"""

    def test_partnership_declaration(self, config):
        """合作关系声明"""
        parts = [('P1', '清华大学与苹果公司联合成立了量子计算实验室，投入50亿元。')]
        decl = detect_declarations(parts, config)
        assert len(decl) >= 1, '应检测到合作关系声明'

    def test_authority_declaration(self, config):
        """权威人物声明"""
        parts = [('P1', '梁文峰博士在公开演讲中宣布公司下一代模型将实现AGI。')]
        decl = detect_declarations(parts, config)
        assert len(decl) >= 1, '应检测到权威声明'

    def test_publication_declaration(self, config):
        """学术成果声明"""
        parts = [('P1', '陈明辉教授在Nature上发表了关于多模态模型幻觉的论文。')]
        decl = detect_declarations(parts, config)
        assert len(decl) >= 1, '应检测到学术成果声明'

    def test_normal_text_no_declaration(self, config):
        """普通文本不应触发声明检测"""
        parts = [('P1', '清华大学位于北京市海淀区。')]
        decl = detect_declarations(parts, config)
        assert len(decl) == 0, '正常描述不应触发声明检测'

    def test_dedup_same_entity(self, config):
        """去重：同声明文本同类别保留最高分"""
        raw = [
            {'word': '清华大学与苹果联合成立实验室', 'category': '声明-合作关系声明', 'score': 45, 'location': 'P1', 'context': '', 'decl_text': ''},
            {'word': '清华大学与苹果联合成立实验室', 'category': '声明-合作关系声明', 'score': 68, 'location': 'P2', 'context': '', 'decl_text': ''},
        ]
        ranked = deduplicate_declarations(raw)
        assert len(ranked) == 1
        assert ranked[0]['score'] == 68

    def test_empty_text(self, config):
        """空文本不触发异常"""
        decl = detect_declarations([('P1', '')], config)
        assert len(decl) == 0

    def test_policy_declaration(self, config):
        """政策文件声明"""
        parts = [('P1', '国家发改委发布了《数字经济2030规划》，目标200万亿元。')]
        decl = detect_declarations(parts, config)
        assert len(decl) >= 1, '应检测到政策声明'
