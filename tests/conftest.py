"""
GEHD 测试套件 - 共享 Fixtures 和辅助函数
===========================================

提供:
- red_team_docx_path: Red Team v2 测试文档路径
- run_check(): 执行docx自检并解析结果的便捷函数
- parse_l4_queue(): 解析L4验证队列JSON
"""

import json
import os
import sys

import pytest

# 确保 src/ 在 sys.path 中（以便 import hallucination_checker）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_PATH = os.path.join(PROJECT_ROOT, 'src')
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# ============================================================
# 路径常量
# ============================================================
# PROJECT_ROOT = .../Claw, 需要上两层到用户home目录才能找到 Desktop
USER_HOME = os.path.dirname(os.path.dirname(PROJECT_ROOT))  # /Users/jingjili
TEST_DATA_DIR = os.path.join(USER_HOME, 'Desktop', 'WorkBuddy', 'GEHD_Test_Suite', 'v2')
RED_TEAM_DOCX = os.path.join(TEST_DATA_DIR, 'GEHD_RedTeam_v2_Document.docx')


@pytest.fixture(scope='session')
def red_team_docx_path():
    """Red Team v2 测试文档路径（session级，只计算一次）"""
    if not os.path.exists(RED_TEAM_DOCX):
        pytest.skip(f'测试文档不存在: {RED_TEAM_DOCX}')
    return RED_TEAM_DOCX


class CheckResult:
    """封装 check_docx() 的返回结果，提供便捷查询方法"""

    def __init__(self, filepath, do_verify=False):
        # 捕获 print 输出
        from io import StringIO

        from hallucination_checker.cli.main import check_docx

        self.captured_output = StringIO()
        old_stdout = sys.stdout
        try:
            sys.stdout = self.captured_output
            self.ok, self.l4_queue = check_docx(filepath, do_verify=do_verify)
        finally:
            sys.stdout = old_stdout

        self.output = self.captured_output.getvalue()
        self.filepath = filepath

    @property
    def issues(self):
        """从输出中提取issue列表（[!] 开头的行）"""
        return [
            line.strip()
            for line in self.output.split('\n')
            if line.strip().startswith(f'{1}.')
            or (line.strip() and line.strip()[0].isdigit() and '[!]' in self.output)
        ]

    @property
    def warnings(self):
        """从输出中提取warning列表（[~] 开头的行）"""
        return [
            line.strip()
            for line in self.output.split('\n')
            if '[数据待核实]' in line or '[实体待核实]' in line or '[一致性' in line
        ]

    def has_issue_containing(self, substring):
        """检查是否存在包含指定文本的 issue"""
        return any(substring in line for line in self.output.split('\n'))

    def has_warning_containing(self, substring):
        """检查是否存在包含指定文本的 warning"""
        return any(substring in line for line in self.output.split('\n'))

    def get_stat_line(self, key):
        """获取统计行中指定key的值"""
        for line in self.output.split('\n'):
            if key in line:
                return line.strip()
        return None

    def l4_words(self):
        """返回L4队列中所有候选词列表"""
        if not self.l4_queue:
            return []
        return [item['word'] for item in self.l4_queue]

    def l4_items_by_layer(self, layer):
        """按source_layer过滤L4队列"""
        if not self.l4_queue:
            return []
        return [item for item in self.l4_queue if item.get('source_layer') == layer]

    def l4_item_by_word(self, word):
        """按word查找L4队列项"""
        if not self.l4_queue:
            return None
        for item in self.l4_queue:
            if item['word'] == word:
                return item
        return None


@pytest.fixture
def check_result(red_team_docx_path):
    """对Red Team文档执行标准检查（不含L4）"""
    return CheckResult(red_team_docx_path, do_verify=False)


@pytest.fixture
def verify_result(red_team_docx_path):
    """对Red Team文档执行完整检查（含L4）"""
    return CheckResult(red_team_docx_path, do_verify=True)


@pytest.fixture
def l4_queue_file(red_team_docx_path):
    """L4队列JSON文件路径（执行verify后生成）"""
    return red_team_docx_path.replace('.docx', '_l4_queue.json')


def load_l4_queue(filepath):
    """加载已生成的L4队列JSON"""
    queue_path = filepath.replace('.docx', '_l4_queue.json')
    if not os.path.exists(queue_path):
        return None
    with open(queue_path, encoding='utf-8') as f:
        return json.load(f)
