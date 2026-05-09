"""GEHD 设置窗口 —— 编辑白名单、黑名单、评分阈值。

独立窗口，关闭时自动写回 config/*.json。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


def get_config_dir() -> Path:
    """查找 config/ 目录（健壮向上查找，与引擎组共享）。

    先尝试当前工作目录，再基于本文件位置向上查找。
    """
    candidates = [
        Path.cwd() / 'config',
        Path(__file__).resolve().parents[5] / 'config',
    ]
    for p in candidates:
        if p.is_dir():
            return p
    raise FileNotFoundError(
        '找不到 config/ 目录。请确保在 GEHD 项目根目录或子目录下运行。'
    )


_CONFIG_DIR: Path = get_config_dir()


def _read_json_array(filepath: Path, key: str) -> list[str]:
    """读 JSON 文件中指定 key 的数组。"""
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        items = data.get(key, [])
        return items if isinstance(items, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _write_json_array(filepath: Path, key: str, items: list[str]) -> None:
    """写入 JSON 文件指定 key 的数组，保留所有其他字段。"""
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data[key] = items
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _read_json_obj(filepath: Path) -> dict[str, Any]:
    """读整个 JSON 文件。"""
    try:
        with open(filepath, encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_json_obj(filepath: Path, data: dict[str, Any]) -> None:
    """写整个 JSON 文件，保留缩进格式。"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class SettingsDialog(QDialog):
    """GEHD 设置独立窗口。

    三个选项卡：
      - 白名单：每行一词，可增删
      - 黑名单：每行一词，可增删
      - 阈值：数值输入框 + 字段说明
    """

    def __init__(self, parent: QDialog | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('GEHD 设置')
        self.setMinimumSize(560, 480)
        self.resize(600, 520)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)

        self._whitelist_path = _CONFIG_DIR / 'whitelist.json'
        self._blacklist_path = _CONFIG_DIR / 'blacklist.json'
        self._thresholds_path = _CONFIG_DIR / 'thresholds.json'

        # 缓存原始阈值数据（用于保留注释字段）
        self._thresholds_data: dict[str, Any] = {}

        self._setup_ui()
        self._load_all()

    # ---- 界面构建 ----

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_whitelist_tab(), '白名单')
        self._tabs.addTab(self._build_blacklist_tab(), '黑名单')
        self._tabs.addTab(self._build_thresholds_tab(), '阈值')
        layout.addWidget(self._tabs)

        close_btn = QPushButton('关闭（自动保存）')
        close_btn.clicked.connect(self._save_and_close)
        layout.addWidget(close_btn)

    # --- 白名单 Tab ---

    def _build_whitelist_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel('白名单词条（每行一个，引擎自动放行）：'))

        btn_layout = QHBoxLayout()
        add_btn = QPushButton('添加空行')
        del_btn = QPushButton('删除当前行')
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._whitelist_edit = QPlainTextEdit()
        self._whitelist_edit.setPlaceholderText('每行一个词，例如：\n华为\n淘宝\nOpenAI')
        layout.addWidget(self._whitelist_edit)

        add_btn.clicked.connect(lambda: self._add_line(self._whitelist_edit))
        del_btn.clicked.connect(lambda: self._del_line(self._whitelist_edit))
        return w

    # --- 黑名单 Tab ---

    def _build_blacklist_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.addWidget(QLabel('黑名单词条（每行一个，引擎直接标记为问题）：'))

        btn_layout = QHBoxLayout()
        add_btn = QPushButton('添加空行')
        del_btn = QPushButton('删除当前行')
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self._blacklist_edit = QPlainTextEdit()
        self._blacklist_edit.setPlaceholderText('每行一个词，例如：\n母丑购\n虚构公司名')
        layout.addWidget(self._blacklist_edit)

        add_btn.clicked.connect(lambda: self._add_line(self._blacklist_edit))
        del_btn.clicked.connect(lambda: self._del_line(self._blacklist_edit))
        return w

    # --- 阈值 Tab ---

    def _build_thresholds_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        w = QWidget()
        scroll.setWidget(w)
        layout = QVBoxLayout(w)

        # 评分阈值组
        score_group = QGroupBox('评分阈值')
        score_form = QFormLayout(score_group)

        self._high_threshold = QSpinBox()
        self._high_threshold.setRange(0, 100)
        self._high_threshold.setToolTip('≥此分的候选标记为高危，直接报告为 issue')
        score_form.addRow('高危阈值 (≥N分标记高危)：', self._high_threshold)

        self._medium_threshold = QSpinBox()
        self._medium_threshold.setRange(0, 100)
        self._medium_threshold.setToolTip('≥此分且<高危线的候选标记为中危，报告为 warning')
        score_form.addRow('中危阈值 (≥N分标记中危)：', self._medium_threshold)

        self._score_minimum = QSpinBox()
        self._score_minimum.setRange(0, 100)
        self._score_minimum.setToolTip('所有候选的最低分数底线')
        score_form.addRow('最低分数：', self._score_minimum)

        self._adjective_penalty = QSpinBox()
        self._adjective_penalty.setRange(0, 100)
        self._adjective_penalty.setToolTip('候选词以形容词前缀开头时的减分幅度')
        score_form.addRow('形容词减分：', self._adjective_penalty)

        self._high_freq_bonus = QSpinBox()
        self._high_freq_bonus.setRange(0, 100)
        self._high_freq_bonus.setToolTip('出现≥3次的候选词加分')
        score_form.addRow('高频加分：', self._high_freq_bonus)

        self._med_freq_bonus = QSpinBox()
        self._med_freq_bonus.setRange(0, 100)
        self._med_freq_bonus.setToolTip('出现≥2次的候选词加分')
        score_form.addRow('中频加分：', self._med_freq_bonus)

        self._plausible_penalty = QSpinBox()
        self._plausible_penalty.setRange(-100, 0)
        self._plausible_penalty.setToolTip('含可信字符时的降分（负数）')
        score_form.addRow('可信字符降分：', self._plausible_penalty)

        layout.addWidget(score_group)

        # L4 阈值组
        l4_group = QGroupBox('L4 验证队列')
        l4_form = QFormLayout(l4_group)

        self._deep_search_threshold = QSpinBox()
        self._deep_search_threshold.setRange(0, 100)
        self._deep_search_threshold.setToolTip('≥此分的候选使用深度搜索（多引擎交叉验证）')
        l4_form.addRow('深度搜索阈值：', self._deep_search_threshold)

        layout.addWidget(l4_group)

        # 文本处理参数组
        text_group = QGroupBox('文本处理')
        text_form = QFormLayout(text_group)

        self._context_window = QSpinBox()
        self._context_window.setRange(0, 200)
        self._context_window.setToolTip('候选词前后抓取的上下文字符数')
        text_form.addRow('上下文窗口（字符）：', self._context_window)

        self._min_candidate_length = QSpinBox()
        self._min_candidate_length.setRange(1, 10)
        self._min_candidate_length.setToolTip('候选实体词的最短长度')
        text_form.addRow('最短候选长度：', self._min_candidate_length)

        layout.addWidget(text_group)
        layout.addStretch()
        return scroll

    # ---- 辅助操作 ----

    @staticmethod
    def _add_line(edit: QPlainTextEdit) -> None:
        cursor = edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        if edit.toPlainText() and not edit.toPlainText().endswith('\n'):
            cursor.insertText('\n')
        edit.setTextCursor(cursor)

    @staticmethod
    def _del_line(edit: QPlainTextEdit) -> None:
        cursor = edit.textCursor()
        cursor.select(cursor.SelectionType.LineUnderCursor)
        cursor.removeSelectedText()
        # 清理多余空行
        text = edit.toPlainText()
        while '\n\n\n' in text:
            text = text.replace('\n\n\n', '\n\n')
        edit.setPlainText(text.strip())

    # ---- 加载与保存 ----

    def _load_all(self) -> None:
        self._load_whitelist()
        self._load_blacklist()
        self._load_thresholds()

    def _load_whitelist(self) -> None:
        items = _read_json_array(self._whitelist_path, 'whitelist')
        self._whitelist_edit.setPlainText('\n'.join(items))

    def _load_blacklist(self) -> None:
        items = _read_json_array(self._blacklist_path, 'blacklist')
        self._blacklist_edit.setPlainText('\n'.join(items))

    def _load_thresholds(self) -> None:
        data = _read_json_obj(self._thresholds_path)
        self._thresholds_data = data

        scores = data.get('scores', {})
        self._high_threshold.setValue(scores.get('high_threshold', 65))
        self._medium_threshold.setValue(scores.get('medium_threshold', 45))
        self._score_minimum.setValue(scores.get('minimum', 10))
        self._adjective_penalty.setValue(
            scores.get('l35_penalty', scores.get('adjective_penalty', 30))
        )
        self._high_freq_bonus.setValue(scores.get('high_freq_bonus', 10))
        self._med_freq_bonus.setValue(scores.get('med_freq_bonus', 3))
        self._plausible_penalty.setValue(scores.get('plausible_char_penalty', -10))

        l4 = data.get('l4', {})
        self._deep_search_threshold.setValue(l4.get('deep_search_threshold', 55))

        text_proc = data.get('text_processing', {})
        self._context_window.setValue(text_proc.get('context_window_chars', 10))
        self._min_candidate_length.setValue(text_proc.get('min_candidate_length', 2))

    def _save_all(self) -> None:
        self._save_whitelist()
        self._save_blacklist()
        self._save_thresholds()

    def _save_whitelist(self) -> None:
        text = self._whitelist_edit.toPlainText().strip()
        items = [line.strip() for line in text.split('\n') if line.strip()]
        _write_json_array(self._whitelist_path, 'whitelist', items)

    def _save_blacklist(self) -> None:
        text = self._blacklist_edit.toPlainText().strip()
        items = [line.strip() for line in text.split('\n') if line.strip()]
        _write_json_array(self._blacklist_path, 'blacklist', items)

    def _save_thresholds(self) -> None:
        data = self._thresholds_data or {}
        scores = data.setdefault('scores', {})
        scores['high_threshold'] = self._high_threshold.value()
        scores['medium_threshold'] = self._medium_threshold.value()
        scores['minimum'] = self._score_minimum.value()
        scores['adjective_penalty'] = self._adjective_penalty.value()
        scores['l35_penalty'] = self._adjective_penalty.value()
        scores['high_freq_bonus'] = self._high_freq_bonus.value()
        scores['med_freq_bonus'] = self._med_freq_bonus.value()
        scores['plausible_char_penalty'] = self._plausible_penalty.value()

        l4 = data.setdefault('l4', {})
        l4['deep_search_threshold'] = self._deep_search_threshold.value()

        text_proc = data.setdefault('text_processing', {})
        text_proc['context_window_chars'] = self._context_window.value()
        text_proc['min_candidate_length'] = self._min_candidate_length.value()

        _write_json_obj(self._thresholds_path, data)

    def _save_and_close(self) -> None:
        try:
            self._save_all()
        except OSError as e:
            QMessageBox.warning(self, '保存失败', f'写入配置文件时出错：{e}')
        self.accept()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """关闭窗口时自动保存。"""
        try:
            self._save_all()
        except OSError:
            pass  # 静默失败，避免阻塞关闭
        super().closeEvent(event)
