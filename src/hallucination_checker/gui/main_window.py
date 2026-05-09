"""GEHD GUI 主窗口 — PySide6 桌面应用。

功能：
  - 加载 .docx 文件（浏览/拖拽/手打路径）
  - 触发同步扫描（gehd_check）
  - 展示 issues / warnings / stats / l4_queue
  - 右键标记候选词（加入白名单/黑名单）
  - 设置窗口（编辑白名单/黑名单/阈值）
  - 重新扫描
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QCheckBox, QLabel, QTabWidget,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QStatusBar, QMenu, QFileDialog, QFrame,
    QMessageBox, QSplitter, QSizePolicy,
)
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import (
    QAction, QColor, QDragEnterEvent, QDropEvent, QFont, QIcon,
)

from hallucination_checker.io.document_text import DocumentText
from hallucination_checker.engine.checker import gehd_check
from hallucination_checker.engine.config import load_config

# 配置目录（与引擎组共享）
_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent / 'config'

# 颜色
_COLOR_ISSUE_BG = QColor('#FFE0E0')        # 浅红
_COLOR_ISSUE_FG = QColor('#B71C1C')         # 深红
_COLOR_WARNING_BG = QColor('#FFF3E0')        # 浅橙
_COLOR_WARNING_FG = QColor('#E65100')        # 深橙
_COLOR_SAFE_BG = QColor('#FFFFFF')           # 白
_COLOR_L4_HIGH_BG = QColor('#FFE0E0')        # L4 队列高危行
_COLOR_L4_MED_BG = QColor('#FFF3E0')         # L4 队列中危行


# ---- 词提取工具 ----

_QUOTED_WORD_RE = re.compile(r'"([^"]+)"')
_GLOSSARY_RE = re.compile(r'虚构词|编造词|可疑实体|疑似幻觉')
_SCORE_RE = re.compile(r'[=≈](\d+)(?:分)?')


def _extract_word_from_issue(text: str) -> str:
    """从 issue/warning 文本中提取目标词（第一个被引号包裹的词）。"""
    m = _QUOTED_WORD_RE.search(text)
    if m:
        return m.group(1)
    return text[:40]


def _word_in_json_array(filepath: Path, key: str, word: str) -> bool:
    """检查词是否已在 JSON 数组中。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get(key, [])
        return word.strip() in items
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def _append_to_json_array(filepath: Path, key: str, word: str) -> None:
    """向 JSON 文件数组追加一个词条（去重）。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    items: list[str] = data.get(key, [])
    w = word.strip()
    if w and w not in items:
        items.append(w)
        data[key] = items
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ---- 拖拽支持 ----

class DropLineEdit(QLineEdit):
    """支持文件拖拽的输入框。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText('选择 .docx 文件，或拖拽到此处，或手动输入路径')

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        mime: QMimeData | None = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.docx'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        mime = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.docx'):
                    self.setText(url.toLocalFile())
                    event.acceptProposedAction()
                    return


# ---- 主窗口 ----

class MainWindow(QMainWindow):
    """GEHD 主窗口。"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('GEHD — 文档幻觉核查工具')
        self.setMinimumSize(860, 600)
        self.resize(960, 700)

        # 状态变量
        self._current_stats: dict[str, int] = {}
        self._current_issues: list[str] = []
        self._current_warnings: list[str] = []
        self._current_l4_queue: list[dict[str, Any]] = []

        self._setup_menu()
        self._setup_ui()
        self._setup_statusbar()

    # ---- 菜单栏 ----

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu('文件')
        open_action = QAction('打开 .docx...', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self._browse_file)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction('退出', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        settings_menu = menubar.addMenu('设置')
        edit_action = QAction('编辑配置...', self)
        edit_action.setShortcut('Ctrl+,')
        edit_action.triggered.connect(self._open_settings)
        settings_menu.addAction(edit_action)

    # ---- 中央区域 ----

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # --- 文件选择行 ---
        file_layout = QHBoxLayout()
        file_layout.setSpacing(6)

        file_label = QLabel('文件路径：')
        self._file_input = DropLineEdit()
        self._file_input.setMinimumWidth(320)

        self._browse_btn = QPushButton('浏览')
        self._browse_btn.clicked.connect(self._browse_file)

        self._verify_checkbox = QCheckBox('生成验证队列')

        self._scan_btn = QPushButton('扫描')
        self._scan_btn.setMinimumWidth(72)
        self._scan_btn.clicked.connect(self._scan)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self._file_input, 1)
        file_layout.addWidget(self._browse_btn)
        file_layout.addWidget(self._verify_checkbox)
        file_layout.addWidget(self._scan_btn)
        layout.addLayout(file_layout)

        # --- 统计条 ---
        self._stats_frame = QFrame()
        self._stats_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self._stats_frame.setStyleSheet(
            'QFrame { background-color: #F5F5F5; border: 1px solid #DDD; '
            'border-radius: 4px; padding: 6px 10px; }'
        )
        stats_layout = QHBoxLayout(self._stats_frame)
        stats_layout.setContentsMargins(12, 4, 12, 4)
        stats_layout.setSpacing(24)

        self._stat_labels: dict[str, QLabel] = {}
        for key in ['total_candidates', 'l25_candidates', 'high_risk',
                     'medium_risk', 'low_risk', 'l4_queue_size']:
            lbl = QLabel('—')
            lbl.setStyleSheet('border: none; background: transparent;')
            stats_layout.addWidget(lbl)
            self._stat_labels[key] = lbl

        stats_layout.addStretch()
        layout.addWidget(self._stats_frame)

        # --- 结果标签页 ---
        self._result_tabs = QTabWidget()

        # 问题标签页 (QListWidget)
        self._issues_list = QListWidget()
        self._issues_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._issues_list.customContextMenuRequested.connect(
            lambda pos: self._on_result_context_menu(pos, self._issues_list, is_issue=True)
        )
        self._result_tabs.addTab(self._issues_list, '问题 (0)')

        # 警告标签页 (QListWidget)
        self._warnings_list = QListWidget()
        self._warnings_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._warnings_list.customContextMenuRequested.connect(
            lambda pos: self._on_result_context_menu(pos, self._warnings_list, is_issue=False)
        )
        self._result_tabs.addTab(self._warnings_list, '警告 (0)')

        # L4 验证队列标签页 (QTableWidget)
        self._l4_table = QTableWidget()
        self._l4_table.setColumnCount(4)
        self._l4_table.setHorizontalHeaderLabels(['词', '分类', '分数', '位置'])
        self._l4_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._l4_table.customContextMenuRequested.connect(self._on_l4_context_menu)
        self._l4_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self._l4_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._l4_table.horizontalHeader().setStretchLastSection(True)
        self._l4_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self._result_tabs.addTab(self._l4_table, '验证队列 (0)')

        layout.addWidget(self._result_tabs, 1)

    # ---- 状态栏 ----

    def _setup_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self._statusbar.showMessage('就绪 — 请选择一个 .docx 文件开始扫描')
        self.setStatusBar(self._statusbar)

    # ---- 浏览文件 ----

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 Word 文档', '',
            'Word 文档 (*.docx);;所有文件 (*)'
        )
        if path:
            self._file_input.setText(path)

    # ---- 扫描 ----

    def _scan(self) -> None:
        filepath = self._file_input.text().strip()
        if not filepath:
            QMessageBox.warning(self, '缺少文件', '请先选择或输入一个 .docx 文件路径。')
            return

        path = Path(filepath)
        if not path.exists():
            QMessageBox.warning(self, '文件不存在', f'找不到文件：\n{filepath}')
            return

        if path.suffix.lower() != '.docx':
            QMessageBox.warning(self, '格式不支持', '当前仅支持 .docx 格式。')
            return

        output_l4 = self._verify_checkbox.isChecked()

        # 禁用按钮，更新状态
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText('扫描中...')
        self._statusbar.showMessage('扫描中...')
        QApplication.processEvents()

        try:
            config = load_config()
            text = DocumentText.from_docx(path)
            issues, warnings, stats, l4_queue = gehd_check(
                text, config, output_verify_queue=output_l4
            )
        except Exception as e:
            self._scan_btn.setEnabled(True)
            self._scan_btn.setText('扫描')
            self._statusbar.showMessage('扫描失败')
            QMessageBox.critical(self, '扫描错误', f'扫描过程中发生错误：\n{e}')
            return

        # 存储结果
        self._current_issues = issues
        self._current_warnings = warnings
        self._current_stats = stats
        self._current_l4_queue = l4_queue

        # 刷新 UI
        self._refresh_stats(stats)
        self._refresh_results(issues, warnings, l4_queue)

        # 恢复按钮
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText('重新扫描')

        issue_count = len(issues)
        self._statusbar.showMessage(
            f'扫描完成，发现 {issue_count} 个问题'
            if issue_count > 0
            else '扫描完成，未发现问题'
        )

    # ---- 统计条刷新 ----

    def _refresh_stats(self, stats: dict[str, int]) -> None:
        mapping: dict[str, str] = {
            'total_candidates':   f'候选实体: {stats.get("total_candidates", 0)}',
            'l25_candidates':     f'L2.5候选: {stats.get("l25_candidates", 0)}',
            'high_risk':          f'高危: {stats.get("high_risk", 0)}',
            'medium_risk':        f'中危: {stats.get("medium_risk", 0)}',
            'low_risk':           f'低危: {stats.get("low_risk", 0)}',
            'l4_queue_size':      f'L4队列: {stats.get("l4_queue_size", 0)}',
        }
        for key, label in self._stat_labels.items():
            label.setText(mapping.get(key, '—'))

    # ---- 结果刷新 ----

    def _refresh_results(
        self,
        issues: list[str],
        warnings: list[str],
        l4_queue: list[dict[str, Any]],
    ) -> None:
        # 清空
        self._issues_list.clear()
        self._warnings_list.clear()
        self._l4_table.setRowCount(0)

        # 问题列表
        for text in issues:
            item = QListWidgetItem(text)
            item.setBackground(_COLOR_ISSUE_BG)
            item.setForeground(_COLOR_ISSUE_FG)
            item.setData(Qt.ItemDataRole.UserRole, text)
            self._issues_list.addItem(item)

        # 警告列表
        for text in warnings:
            item = QListWidgetItem(text)
            item.setBackground(_COLOR_WARNING_BG)
            item.setForeground(_COLOR_WARNING_FG)
            item.setData(Qt.ItemDataRole.UserRole, text)
            self._warnings_list.addItem(item)

        # L4 队列表格
        self._l4_table.setRowCount(len(l4_queue))
        for row, entry in enumerate(l4_queue):
            word = entry.get('word', '')
            category = entry.get('category', '')
            score = entry.get('score', 0)
            location = entry.get('location', '')

            self._l4_table.setItem(row, 0, QTableWidgetItem(word))
            self._l4_table.setItem(row, 1, QTableWidgetItem(category))

            score_item = QTableWidgetItem()
            score_item.setData(Qt.ItemDataRole.DisplayRole, score)
            self._l4_table.setItem(row, 2, score_item)

            self._l4_table.setItem(row, 3, QTableWidgetItem(location))

            # 高危/中危行着色
            if score >= 65:
                for col in range(4):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(_COLOR_L4_HIGH_BG)
            elif score >= 45:
                for col in range(4):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(_COLOR_L4_MED_BG)

        # 更新标签
        self._result_tabs.setTabText(0, f'问题 ({len(issues)})')
        self._result_tabs.setTabText(1, f'警告 ({len(warnings)})')
        self._result_tabs.setTabText(2, f'验证队列 ({len(l4_queue)})')

    # ---- 右键菜单：问题/警告列表 ----

    def _on_result_context_menu(
        self,
        pos,
        list_widget: QListWidget,
        is_issue: bool,
    ) -> None:
        item = list_widget.currentItem()
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole) or item.text()
        word = _extract_word_from_issue(text)
        self._show_context_menu(pos, list_widget, word, item)

    # ---- 右键菜单：L4 队列表格 ----

    def _on_l4_context_menu(self, pos) -> None:
        row = self._l4_table.currentRow()
        if row < 0:
            return
        word_item = self._l4_table.item(row, 0)
        if not word_item:
            return
        word = word_item.text()
        self._show_context_menu(
            pos, self._l4_table, word, row=row
        )

    # ---- 右键菜单核心 ----

    def _show_context_menu(
        self,
        pos,
        widget: QListWidget | QTableWidget,
        word: str,
        item: QListWidgetItem | None = None,
        *,
        row: int = -1,
    ) -> None:
        menu = QMenu(self)

        real_action = QAction('确认真实', self)
        real_action.triggered.connect(lambda: self._mark_word(word, 'real', widget, item, row))
        menu.addAction(real_action)

        fake_action = QAction('确认幻觉', self)
        fake_action.triggered.connect(lambda: self._mark_word(word, 'fake', widget, item, row))
        menu.addAction(fake_action)

        menu.exec(widget.viewport().mapToGlobal(pos))

    def _mark_word(
        self,
        word: str,
        action: str,
        widget: QListWidget | QTableWidget,
        item: QListWidgetItem | None,
        row: int,
    ) -> None:
        if action == 'real':
            target_file = _CONFIG_DIR / 'whitelist.json'
            target_key = 'whitelist'
        else:
            target_file = _CONFIG_DIR / 'blacklist.json'
            target_key = 'blacklist'

        if _word_in_json_array(target_file, target_key, word):
            QMessageBox.information(
                self, '已存在',
                f'"{word}" 已在{("白名单" if action == "real" else "黑名单")}中。'
            )
            return

        try:
            _append_to_json_array(target_file, target_key, word)
        except OSError as e:
            QMessageBox.warning(self, '写入失败', f'写入配置文件时出错：{e}')
            return

        # 从当前列表中移除
        if isinstance(widget, QListWidget) and item is not None:
            row_idx = widget.row(item)
            widget.takeItem(row_idx)
            if widget is self._issues_list:
                self._result_tabs.setTabText(0, f'问题 ({self._issues_list.count()})')
            else:
                self._result_tabs.setTabText(1, f'警告 ({self._warnings_list.count()})')
        elif isinstance(widget, QTableWidget) and row >= 0:
            widget.removeRow(row)
            self._result_tabs.setTabText(2, f'验证队列 ({widget.rowCount()})')

    # ---- 设置窗口 ----

    def _open_settings(self) -> None:
        from hallucination_checker.gui.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self)
        dialog.setWindowModality(Qt.WindowModality.NonModal)
        dialog.show()
        # 保持引用防止被 GC
        self._settings_dialog = dialog


# ---- 入口 ----

def main() -> None:
    """启动 GEHD GUI 应用。"""
    app = QApplication(sys.argv)
    app.setApplicationName('GEHD')
    app.setApplicationVersion('0.2.0')

    # 系统默认样式
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
