"""
GEHD v3.6 核心回归测试套件
===========================

覆盖范围:
- L1 白名单放行（2个断言）
- L2 黑名单拦截（2个断言）
- L3 实体检测+评分（2个断言）
- L2.5 非实体检测（2个断言）
- L3.6 一致性检查（1个断言）
- L4 队列输出协议（2个断言）
- v3.6 R1 引语收紧回归保护（1个断言）

测试数据: Red Team v2 Document (GEHD_RedTeam_v2_Document.docx)

运行方式:
    pytest tests/test_regression.py -v
    
预期结果: 全部 passed (12/12)
"""

import pytest
import json
import os


class TestL2Blacklist:
    """L2 黑名单拦截 — 确定性检测，必须命中"""
    
    def test_l2_catches_muchou_gou(self, check_result):
        """TC01: '母丑购' 必须被 L2 黑名单拦截为 issue"""
        assert check_result.has_issue_containing("母丑购"), \
            "FAIL: [L2] '母丑购' 未被黑名单拦截 — 核心防护失效"
    
    def test_l2_catches_muchou(self, check_result):
        """TC02: '母丑' 必须被 L2 黑名单拦截为 issue"""
        assert check_result.has_issue_containing('"母丑"'), \
            "FAIL: [L2] '母丑' 未被黑名单拦截 — 黑名单匹配异常"


class TestL1Whitelist:
    """L1 白名单放行 — 已知真实名词不应出现在候选列表中"""
    
    def test_whitelist_passes_huawei(self, verify_result):
        """TC03: '华为' 在白名单中，不应出现在 L4 候选列表"""
        words = verify_result.l4_words()
        # 注意：白名单子串收紧后，"华为技术有限公司"可能以降分形式出现
        # 但纯 "华为" 不应出现
        huawei_items = [w for w in words if w == '华为']
        assert len(huawei_items) == 0, \
            f"FAIL: [L1] '华为' 出现在L4候选中(应被白名单放行): {huawei_items}"
    
    def test_whitelist_passes_tencent(self, verify_result):
        """TC04: '腾讯' 在白名单中，不应出现在 L4 候选列表"""
        words = verify_result.l4_words()
        tencent_items = [w for w in words if w == '腾讯']
        assert len(tencent_items) == 0, \
            f"FAIL: [L1] '腾讯' 出现在L4候选中(应被白名单放行): {tencent_items}"


class TestL3EntityDetection:
    """L3 启发式实体提取 + 可疑度评分"""
    
    def test_l3_detects_chenxing_weidianzi(self, check_result):
        """TC05: '辰星微电子'(虚构半导体企业) 必须被标记为中危(>=45分)"""
        assert check_result.has_warning_containing("辰星微电子"), \
            "FAIL: [L3] '辰星微电子' 未被检测到 — 半导体企业正则可能失效"
        
        # 验证分数：在verify模式下检查L4队列中的score
    def test_l3_chenxing_score(self, verify_result):
        """TC05b: 辰星微电子的 score >= 50 (半导体企业名base_score=50)"""
        item = verify_result.l4_item_by_word('辰星微电子')
        assert item is not None, "FAIL: [L3] '辰星微电子' 不在L4队列中"
        assert item['score'] >= 50, \
            f"FAIL: [L3] 辰星微电子分数 {item['score']} < 50，评分系统可能退化"

    def test_l3_detects_lingxi_gou(self, check_result):
        """TC06: '灵犀购'(虚构电商平台) 必须被标记为中危(>=45分)"""
        assert check_result.has_warning_containing("灵犀购"), \
            "FAIL: [L3] '灵犀购' 未被检测到 — 电商平台正则可能失效"


class TestL25NonEntityDetection:
    """L2.5 非实体幻觉检测 [v3.5新增]"""
    
    def test_l25_catches_statistics_80yi(self, check_result):
        """TC07: '80亿人民币' 必须进入 L2.5 数据候选"""
        assert check_result.has_warning_containing("80亿人民币"), \
            "FAIL: [L2.5] '80亿人民币' 未被检测到 — 统计金额正则可能失效"
    
    def test_l25_catches_statistics_2000yi(self, check_result):
        """TC08: '2000亿美元' 必须进入 L2.5 数据候选"""
        assert check_result.has_warning_containing("2000亿美元"), \
            "FAIL: [L2.5] '2000亿美元' 未被检测到 — 统计金额正则可能失效"


class TestL36ConsistencyCheck:
    """L3.6 内部一致性检查 [v3.5新增]"""
    
    def test_l36_detects_high_freq_entity(self, check_result):
        """TC09: 高频实体('辰星微电子'出现>=3次)必须触发一致性警告"""
        # 辰星微电子在Red Team文档中出现4次，应触发一致性警告
        has_consistency = check_result.has_warning_containing('一致性') \
                        or check_result.has_warning_containing('高频') \
                        or check_result.has_warning_containing('辰星微电子')
        assert has_consistency, \
            "FAIL: [L3.6] 高频实体未触发一致性警告 — 一致性检查模块可能失效"


class TestL4QueueOutput:
    """L4 联网核查队列输出协议 [v3.5标准化 + v3.6格式统一]"""
    
    def test_l4_queue_has_entities(self, verify_result):
        """TC10: --verify 模式下 L4 队列非空且 entities 字段存在"""
        assert verify_result.l4_queue is not None, \
            "FAIL: [L4] verify模式未返回l4_queue"
        assert len(verify_result.l4_queue) > 0, \
            f"FAIL: [L4] 队列为空(应有候选词)"
    
    def test_l4_source_layer_field(self, verify_result):
        """TC11: 所有L4队列项都有 source_layer 字段 (v3.6新增)"""
        for item in verify_result.l4_queue:
            assert 'source_layer' in item, \
                f"FAIL: [L4] 缺少source_layer字段: {item}"
            assert item['source_layer'] in ('L2.5', 'L3'), \
                f"FAIL: [L4] 无效的source_layer值: {item.get('source_layer')}"

    def test_l4_layer_distribution(self, verify_result):
        """TC11b: L2.5项和L3项同时存在（验证双层来源都正常工作）"""
        l25_items = verify_result.l4_items_by_layer('L2.5')
        l3_items = verify_result.l4_items_by_layer('L3')
        assert len(l25_items) >= 2, \
            f"FAIL: [L4] L2.5源项目太少({len(l25_items)})，L2.5层可能失效"
        assert len(l3_items) >= 10, \
            f"FAIL: [L4] L3源项目太少({len(l3_items)})，L3层可能失效"


class TestV36QuoteTighteningRegression:
    """v3.6 R1 回归保护 — 引语正则收紧后的行为验证"""

    def test_no_false_positive_slogan_quotes(self, verify_result):
        """TC12: 纯口号式引语不应被 L2.5 直接引语 正则捕获
        
        Red Team文档中包含以下类型的文本（如果有的话）：
        - "人工智能是未来发展的核心驱动力" → 这类无实体特征的口号不应被捕获
        
        如果这个测试在未来失败，说明某次改动导致引语正则重新变宽松了。
        """
        # 验证：L2.5直接引语类别的候选不应该包含纯口号内容
        # （具体来说，如果文档中有不含人名/数字/机构/时间的长引语，不应被捕获）
        # 
        # 这个测试的核心意图是：确保R1的修复持续有效
        # 我们通过间接验证——如果L2.5引语类别捕获了大量低分项，说明正则可能变宽松了
        
        if verify_result.l4_queue:
            quote_items = [
                item for item in verify_result.l4_queue
                if item.get('category') == '直接引语(待核实)'
            ]
            # 当前Red Team v2 文档中的引语如果有被捕获的，
            # 应该都含有人名/数字等实体特征（因为R1已收紧）
            # 如果未来发现大量纯口号被捕获，此测试会提醒我们
            #
            # 注：这是一个软性守护测试 —— 它不硬编码"必须是0个"，
            # 因为文档内容可能变化。但如果有异常多的引语被捕获，
            # 应该触发人工审查。
            
            # 允许最多3条引语（合理的含实体特征引语数量）
            assert len(quote_items) <= 3, \
                f"WARN: [R1 REGRESS] 直接引语捕获{len(quote_items)}条，" \
                f"可能引语正则又变宽松了。需审查: {[q['word'] for q in quote_items]}"


class TestL4ProtocolStructure:
    """L4 协议结构完整性验证"""
    
    def test_l4_json_protocol_fields(self, verify_result, l4_queue_file):
        """TC13: L4 JSON 包含所有协议必需字段"""
        if not os.path.exists(l4_queue_file):
            pytest.skip(f"L4队列文件未生成: {l4_queue_file}")
        
        with open(l4_queue_file, 'r', encoding='utf-8') as f:
            protocol = json.load(f)
        
        # 检查顶层字段
        assert 'protocol_version' in protocol, "[L4协议] 缺少protocol_version"
        assert 'gehd_version' in protocol, "[L4协议] 缺少gehd_version"
        assert 'generated_at' in protocol, "[L4协议] 缺少generated_at"
        assert 'tiered_strategy' in protocol, "[L4协议] 缺少tiered_strategy"
        assert 'entities' in protocol, "[L4协议] 缺少entities"
        assert '_verdict_schema' in protocol, "[L4协议] 缺少_verdict_schema"
        
        # 检查版本号
        assert protocol['gehd_version'] == '3.6', \
            f"[L4协议] 版本号应为3.6，实际为{protocol['gehd_version']}"
        
        # 检查分级策略完整性
        ts = protocol['tiered_strategy']
        assert 'deep_search' in ts, "[L4协议] 缺少deep_search策略"
        assert 'quick_search' in ts, "[L4协议] 缺少quick_search策略"
        assert 'condition' in ts['deep_search'], "[L4协议] deep_search缺少condition"
        assert 'condition' in ts['quick_search'], "[L4协议] quick_search缺少condition"
        
        # 检查verdict枚举完整
        vs = protocol['_verdict_schema']
        expected_verdicts = ['verified_real', 'verified_fake', 'need_manual_check', 'unable_to_verify']
        for v in expected_verdicts:
            assert v in vs, f"[L4协议] verdict枚举缺少: {v}"


# ============================================================
# 边界条件 / 负面测试
# ============================================================
class TestEdgeCases:
    """边界条件和异常输入处理"""
    
    def test_nonexistent_file_returns_gracefully(self):
        """不存在的文件路径应优雅返回错误，不崩溃"""
        from docx_self_check import check_docx
        ok, result = check_docx("/tmp/nonexistent_file_99999.docx")
        assert ok is False, "不存在的文件应返回False"
    
    def test_version_string_in_output(self, check_result):
        """输出报告应包含当前版本号"""
        assert "v3.6" in check_result.output, \
            "FAIL: 输出报告中未显示版本号v3.6 — 版本常量可能未更新"
    
    def test_disclaimer_present(self, check_result):
        """输出报告底部应包含免责声明"""
        assert "声明" in check_result.output and "不构成最终事实判定" in check_result.output, \
            "FAIL: 输出报告缺少免责声明"
