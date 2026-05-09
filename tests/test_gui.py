"""GEHD GUI 测试。

测试范围：
  - 模块导入完整性
  - 词提取工具函数
  - 配置读写函数
  - 主窗口和设置对话框的创建
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from hallucination_checker.gui.main_window import (
    _append_to_json_array,
    _extract_word_from_issue,
    _word_in_json_array,
)
from hallucination_checker.gui.settings_dialog import (
    _read_json_array,
    _read_json_obj,
    _write_json_array,
    _write_json_obj,
)

# ---- 词提取测试 ----

class TestWordExtraction:
    """_extract_word_from_issue 测试。"""

    def test_extract_from_issue_with_quoted_word(self) -> None:
        text = '[幻觉-L2] P38 虚构词 "母丑购": "有用户反映在母丑购购买..."'
        assert _extract_word_from_issue(text) == '母丑购'

    def test_extract_from_warning_with_quoted_word(self) -> None:
        text = '[数据待核实] [可疑统计金额=48] P15 "80亿人民币"'
        assert _extract_word_from_issue(text) == '80亿人民币'

    def test_extract_no_quotes_returns_prefix(self) -> None:
        text = '没有引号的文本内容很长很长很长很长很长'
        result = _extract_word_from_issue(text)
        assert len(result) <= 40
        assert result == text[:40]

    def test_extract_empty_string(self) -> None:
        assert _extract_word_from_issue('') == ''

    def test_extract_single_char_word(self) -> None:
        text = '某个词 "A": 描述'
        assert _extract_word_from_issue(text) == 'A'


# ---- JSON 配置读写测试 ----

class TestJsonConfigOperations:
    """config JSON 读写函数测试。"""

    def test_read_write_json_array_roundtrip(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            f.write('{"test_key": ["a", "b", "c"], "_note": "comment"}')
            tmp_path = f.name

        try:
            items = _read_json_array(Path(tmp_path), 'test_key')
            assert items == ['a', 'b', 'c']

            _write_json_array(Path(tmp_path), 'test_key', ['x', 'y'])
            items2 = _read_json_array(Path(tmp_path), 'test_key')
            assert items2 == ['x', 'y']

            # 验证注释字段被保留
            data = _read_json_obj(Path(tmp_path))
            assert data.get('_note') == 'comment'
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_read_nonexistent_file(self) -> None:
        items = _read_json_array(Path('/nonexistent/path.json'), 'key')
        assert items == []

    def test_read_nonexistent_key(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            f.write('{"other": [1, 2, 3]}')
            tmp_path = f.name

        try:
            items = _read_json_array(Path(tmp_path), 'missing_key')
            assert items == []
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_write_creates_file(self) -> None:
        with tempfile.NamedTemporaryFile(
            suffix='.json', delete=False
        ) as f:
            tmp_path = f.name

        try:
            _write_json_array(Path(tmp_path), 'new_key', ['hello'])
            items = _read_json_array(Path(tmp_path), 'new_key')
            assert items == ['hello']
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_word_in_json_array_true(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump({'test_list': ['foo', 'bar', 'baz']}, f)
            tmp_path = f.name

        try:
            assert _word_in_json_array(Path(tmp_path), 'test_list', 'bar') is True
            assert _word_in_json_array(Path(tmp_path), 'test_list', 'nope') is False
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_append_to_json_array_dedup(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump({'mylist': ['existing']}, f)
            tmp_path = f.name

        try:
            _append_to_json_array(Path(tmp_path), 'mylist', 'new_word')
            items = _read_json_array(Path(tmp_path), 'mylist')
            assert 'new_word' in items
            assert items.count('new_word') == 1

            # 重复添加不应重复
            _append_to_json_array(Path(tmp_path), 'mylist', 'new_word')
            items = _read_json_array(Path(tmp_path), 'mylist')
            assert items.count('new_word') == 1
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_read_write_json_obj_preserves_structure(self) -> None:
        original = {
            'scores': {'high_threshold': 65, 'medium_threshold': 45},
            '_description': 'test config',
            'l4': {'deep_search_threshold': 55},
        }
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.json', delete=False, encoding='utf-8'
        ) as f:
            json.dump(original, f, indent=2)
            tmp_path = f.name

        try:
            data = _read_json_obj(Path(tmp_path))
            assert data['_description'] == 'test config'
            assert data['scores']['high_threshold'] == 65

            data['scores']['high_threshold'] = 75
            _write_json_obj(Path(tmp_path), data)

            data2 = _read_json_obj(Path(tmp_path))
            assert data2['scores']['high_threshold'] == 75
            assert data2['_description'] == 'test config'
        finally:
            Path(tmp_path).unlink(missing_ok=True)


# ---- GUI 组件创建测试 ----

class TestGuiCreation:
    """验证 GUI 组件可正常实例化（无 QApplication 时仅检查导入）。"""

    def test_main_window_class_exists(self) -> None:
        from hallucination_checker.gui.main_window import MainWindow
        assert MainWindow is not None

    def test_settings_dialog_class_exists(self) -> None:
        from hallucination_checker.gui.settings_dialog import SettingsDialog
        assert SettingsDialog is not None

    def test_drop_line_edit_class_exists(self) -> None:
        from hallucination_checker.gui.main_window import DropLineEdit
        assert DropLineEdit is not None

    def test_main_entry_exists(self) -> None:
        from hallucination_checker.gui.main_window import main
        assert callable(main)

    def test_package_exports(self) -> None:
        from hallucination_checker.gui import main as gui_main
        assert callable(gui_main)
