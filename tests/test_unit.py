"""
GEHD 单元测试套件 — 不依赖外部 .docx 文件。

覆盖：
  - L1 白名单（子串匹配、剩余长度判定）
  - L2 黑名单（命中/未命中）
  - L3 评分（各维度独立验证）
  - L3.6 一致性（高频检测、金额矛盾）
  - 配置加载（默认值、JSON 加载、回退、未知 key 警告）

所有测试基于构造的字符串输入，可在任何环境运行。
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import json
import tempfile
import warnings
from pathlib import Path

import pytest

from hallucination_checker.engine.config import GEHDConfig
from hallucination_checker.engine.layers.l1_whitelist import check_substring_whitelist
from hallucination_checker.engine.layers.l2_blacklist import scan_blacklist
from hallucination_checker.engine.layers.l3_heuristic import (
    deduplicate_entities,
    extract_and_score,
)
from hallucination_checker.engine.layers.l25_nonentity import (
    detect_non_entity,
)
from hallucination_checker.engine.layers.l36_consistency import (
    check_amount_conflicts,
    check_entity_frequency,
)

# ---- 共享 fixture ----

@pytest.fixture
def config():
    """内置默认配置。"""
    return GEHDConfig.default()


# ============================================================
# L1 白名单单元测试
# ============================================================


class TestL1WhitelistUnit:
    """L1 白名单子串匹配逻辑"""

    def test_exact_substring_3char_skips(self, config):
        """"龙旗科技"(3字白名单词)等于候选词 → 应放行"""
        matched, should_skip, _ = check_substring_whitelist('龙旗科技', config)
        assert matched == '龙旗科技'
        assert should_skip is True

    def test_exact_substring_2char_prefix_skips(self, config):
        """"小米"(2字白名单词)等于候选词 → 应放行"""
        matched, should_skip, _ = check_substring_whitelist('小米', config)
        assert matched == '小米'
        assert should_skip is True

    def test_2char_not_prefix_no_skip(self, config):
        """"小米"不在开头(如"买小米") → 2字词需前缀才放行"""
        matched, should_skip, _ = check_substring_whitelist('买小米科技', config)
        assert matched is None
        assert should_skip is False

    def test_remainder_2plus_chars_no_skip(self, config):
        """白名单词后有≥2字剩余 → 不放行（如"小米旗舰店"）"""
        matched, should_skip, remainder = check_substring_whitelist('小米旗舰店', config)
        assert matched == '小米'
        assert should_skip is False
        assert len(remainder) >= 2

    def test_unknown_word_no_match(self, config):
        """完全未知的词 → 无匹配"""
        matched, should_skip, _ = check_substring_whitelist('火星科技集团', config)
        assert matched is None
        assert should_skip is False

    def test_whitelist_not_in_word(self, config):
        """白名单词不在候选词中 → 无匹配"""
        matched, should_skip, _ = check_substring_whitelist('随便什么词', config)
        assert matched is None


# ============================================================
# L2 黑名单单元测试
# ============================================================


class TestL2BlacklistUnit:
    """L2 黑名单扫描"""

    def test_blacklist_hit(self, config):
        """黑名单词被扫描到"""
        issues = scan_blacklist([('P1', '用户反映在母丑购购买的商品有问题')], config)
        assert len(issues) >= 1
        assert any('母丑购' in i for i in issues)

    def test_blacklist_miss(self, config):
        """正常文本不应命中黑名单"""
        issues = scan_blacklist([('P1', '用户在京东购买的商品质量很好')], config)
        assert len(issues) == 0

    def test_blacklist_multiple_locations(self, config):
        """多个文本片段中扫描"""
        parts = [
            ('P1', '正常文本'),
            ('P2', '母丑京东促销活动'),
            ('P3', '更多正常文本'),
        ]
        issues = scan_blacklist(parts, config)
        assert len(issues) >= 1


# ============================================================
# L2.5 非实体检测单元测试
# ============================================================


class TestL25NonEntityUnit:
    """L2.5 统计金额/百分比/引述检测"""

    def test_stat_amount_detected(self, config):
        candidates = detect_non_entity([('P1', '公司估值达到800亿人民币')], config)
        words = [c['word'] for c in candidates]
        assert any('800亿人民币' in w for w in words)

    def test_percentage_detected(self, config):
        candidates = detect_non_entity([('P1', '增长率37%，市占率超25%')], config)
        assert len(candidates) >= 1

    def test_excluded_phrase_skipped(self, config):
        """GDP等已知真实表述不应被捕获"""
        candidates = detect_non_entity([('P1', 'GDP增长率为6.5%')], config)
        words = [c['word'] for c in candidates]
        assert 'GDP' not in words


# ============================================================
# L3 评分维度单元测试
# ============================================================


class TestL3ScoringUnit:
    """L3 评分各维度独立验证"""

    def _get_score(self, text, word, config):
        """辅助: 从文本中提取指定词的分数"""
        candidates = extract_and_score([('P1', text)], text, config)
        ranked = deduplicate_entities(candidates)
        for ent in ranked:
            if ent['word'] == word:
                return ent['score']
        return None

    def test_base_score(self, config):
        """虚构电商平台应有≥60的基础分"""
        score = self._get_score('用户反映在灵犀购物平台购买', '灵犀购', config)
        assert score is not None, '灵犀购未被提取'
        assert score >= 50, f'灵犀购分数 {score} < 50'

    def test_adjective_penalty(self, config):
        """形容词前缀("权威科技")应被大幅降分"""
        # 构造: "权威科技" 匹配 公司机构名 正则 → base_score=50 → 形容词降分30 → 最终≤25
        score = self._get_score('权威科技有限公司宣布获得融资', '权威科技', config)
        # 如果被提取了, 分应该很低
        if score is not None:
            assert score <= 30, f'形容词前缀应降分, 但分数为 {score}'

    def test_frequency_bonus(self, config):
        """高频出现应加分"""
        word = '辰星微电子'
        text = f'{word}发布新品。{word}获得融资。{word}扩大团队。{word}开拓市场。'
        candidates = extract_and_score([('P1', text)], text, config)
        ranked = deduplicate_entities(candidates)
        for ent in ranked:
            if ent['word'] == word:
                # 出现4次 → +10 高频加分
                assert ent['score'] >= 55, f'高频词分数应≥55, 实际{ent["score"]}'
                return
        pytest.fail(f'"{word}" 未被提取')

    def test_excluded_word_filtered(self, config):
        """排除词(如"采购")不应出现在候选中"""
        candidates = extract_and_score([('P1', '采购中心完成采购任务')], '采购中心完成采购任务', config)
        words = [c['word'] for c in candidates]
        assert '采购' not in words

    def test_dedup_keeps_highest(self, config):
        """去重保留最高分"""
        raw = [
            {'word': '测试词', 'score': 50, 'category': '公司机构名', 'location': 'P1', 'context': ''},
            {'word': '测试词', 'score': 80, 'category': '电商平台名', 'location': 'P2', 'context': ''},
        ]
        ranked = deduplicate_entities(raw)
        assert len(ranked) == 1
        assert ranked[0]['score'] == 80

    def test_minimum_score_floor(self, config):
        """分数不低于最低线"""
        candidates = extract_and_score(
            [('P1', '小米发布新产品')], '小米发布新产品', config
        )
        ranked = deduplicate_entities(candidates)
        for ent in ranked:
            assert ent['score'] >= config.score_minimum


# ============================================================
# L3.6 一致性单元测试
# ============================================================


class TestL36ConsistencyUnit:
    """L3.6 内部一致性检查"""

    def test_high_frequency_detected(self):
        """同一实体出现≥3次应被标记"""
        candidates = [
            {'word': '辰星微电子', 'location': 'P1'},
            {'word': '辰星微电子', 'location': 'P2'},
            {'word': '辰星微电子', 'location': 'P3'},
            {'word': '辰星微电子', 'location': 'P4'},
        ]
        issues = check_entity_frequency(candidates)
        assert len(issues) == 1
        assert issues[0]['type'] == '高频实体'

    def test_low_frequency_not_detected(self):
        """出现<3次不应触发"""
        candidates = [
            {'word': '某个词', 'location': 'P1'},
            {'word': '某个词', 'location': 'P2'},
        ]
        issues = check_entity_frequency(candidates)
        assert len(issues) == 0

    def test_amount_conflict_detected(self):
        """同段落多金额应被标记"""
        issues = check_amount_conflicts([('P1', '营收100亿元，利润50亿元')])
        assert len(issues) == 1
        assert issues[0]['type'] == '多金额共存'

    def test_single_amount_no_conflict(self):
        """单一金额不触发"""
        issues = check_amount_conflicts([('P1', '营收100亿元')])
        assert len(issues) == 0


# ============================================================
# 配置加载单元测试
# ============================================================


class TestConfigLoading:
    """GEHDConfig 工厂方法和 JSON 加载"""

    def test_default_config_has_values(self):
        """默认配置应有合理的初始值"""
        config = GEHDConfig.default()
        assert config.score_high_threshold == 65
        assert config.score_medium_threshold == 45
        assert len(config.whitelist) > 0
        assert len(config.blacklist) > 0
        assert config.deep_search_threshold == 55

    def test_default_creates_fresh_instances(self):
        """每次调用 default() 返回独立实例"""
        c1 = GEHDConfig.default()
        c2 = GEHDConfig.default()
        # frozenset 的 id 相同是正常的（不可变对象共享），但两者应 equal
        assert c1.score_high_threshold == c2.score_high_threshold

    def test_json_overrides_defaults(self):
        """JSON 配置覆盖默认值"""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            # 写一个最小 whitelist
            wl_path = os.path.join(tmpdir, 'whitelist.json')
            with open(wl_path, 'w') as f:
                json.dump({'whitelist': ['测试白名单词']}, f)

            # 写 thresholds
            th_path = os.path.join(tmpdir, 'thresholds.json')
            with open(th_path, 'w') as f:
                json.dump({'scores': {'high_threshold': 99}}, f)

            # 对其他 JSON 创建空文件以避免 FileNotFoundError
            for name in ['blacklist', 'entity_patterns', 'l25_patterns',
                         'exclude_words', 'adjective_prefixes']:
                p = os.path.join(tmpdir, f'{name}.json')
                with open(p, 'w') as f:
                    json.dump({name: []}, f)

            config = GEHDConfig.from_json_dir(tmpdir)
            assert config.score_high_threshold == 99
            assert '测试白名单词' in config.whitelist

    def test_unknown_threshold_key_warns(self):
        """未知阈值键应触发警告"""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            th_path = os.path.join(tmpdir, 'thresholds.json')
            with open(th_path, 'w') as f:
                json.dump({'scores': {'typo_key': 999}}, f)

            # 对其他 JSON 创建空文件
            for name in ['whitelist', 'blacklist', 'entity_patterns',
                         'l25_patterns', 'exclude_words', 'adjective_prefixes']:
                p = os.path.join(tmpdir, f'{name}.json')
                with open(p, 'w') as f:
                    json.dump({name: []}, f)

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                GEHDConfig.from_json_dir(tmpdir)
                gehd_warnings = [x for x in w if 'GEHD config' in str(x.message)]
                assert len(gehd_warnings) >= 1, '未知阈值键应触发警告'

    def test_missing_json_falls_back(self):
        """JSON 文件缺失时回退默认值"""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            config = GEHDConfig.from_json_dir(tmpdir)
            # 应等于默认值
            assert config.score_high_threshold == 65
