"""GEHD GUI 主窗口 — PySide6 桌面应用。v0.3.0。

功能：
  - 加载 .docx 文件（浏览/拖拽/手打路径）
  - 触发同步扫描（gehd_check）
  - 展示 issues / warnings / stats / l4_queue（含验证状态和证据链）
  - 右键标记候选词（加入白名单/黑名单）
  - 设置窗口（编辑白名单/黑名单/阈值/l4_auto_verify）
  - 一键执行建议操作
  - 重新扫描
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import (
    QAction,
    QColor,
    QDragEnterEvent,
    QDropEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from hallucination_checker.engine.checker import gehd_check
from hallucination_checker.engine.config import GEHD_VERSION, load_config
from hallucination_checker.engine.cross_validate import gehd_cross_validate
from hallucination_checker.gui.settings_dialog import get_config_dir
from hallucination_checker.io.document_text import DocumentText

# 配置目录（与引擎组共享，不私存）
_CONFIG_DIR = get_config_dir()

# ---- 颜色常量 ----
_COLOR_ISSUE_BG = QColor('#FFE0E0')
_COLOR_ISSUE_FG = QColor('#B71C1C')
_COLOR_WARNING_BG = QColor('#FFF3E0')
_COLOR_WARNING_FG = QColor('#E65100')
_COLOR_L4_HIGH_BG = QColor('#FFE0E0')
_COLOR_L4_MED_BG = QColor('#FFF3E0')

# L4 验证状态颜色
_COLOR_VERIFIED_REAL_BG = QColor('#E8F5E9')       # 绿
_COLOR_VERIFIED_REAL_FG = QColor('#2E7D32')
_COLOR_VERIFIED_FAKE_BG = QColor('#FFEBEE')       # 红
_COLOR_VERIFIED_FAKE_FG = QColor('#C62828')
_COLOR_NEED_MANUAL_BG = QColor('#FFF8E1')          # 琥珀
_COLOR_NEED_MANUAL_FG = QColor('#E65100')
_COLOR_UNABLE_BG = QColor('#F5F5F5')              # 灰
_COLOR_UNABLE_FG = QColor('#757575')

# L4 交叉校验共识颜色
_COLOR_STRONG_CONSENSUS_BG = QColor('#C8E6C9')    # 深绿
_COLOR_WEAK_CONSENSUS_BG = QColor('#E8F5E9')      # 浅绿
_COLOR_DIVERGENT_BG = QColor('#F5F5F5')           # 灰

# L4 状态 → 中文标签
_STATUS_LABELS: dict[str, str] = {
    'verified_real': '已验证真',
    'verified_fake': '已验证假',
    'need_manual_check': '需人工复核',
    'unable_to_verify': '无法验证',
    'pending': '待验证',
}

# ---- 工具函数 ----
_QUOTED_WORD_RE = re.compile(r'"([^"]+)"')


def _extract_word_from_issue(text: str) -> str:
    m = _QUOTED_WORD_RE.search(text)
    if m:
        return m.group(1)
    return text[:40]


def _word_in_json_array(filepath: Path, key: str, word: str) -> bool:
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        return word.strip() in data.get(key, [])
    except (FileNotFoundError, json.JSONDecodeError):
        return False


def _append_to_json_array(filepath: Path, key: str, word: str) -> None:
    try:
        with open(filepath, encoding='utf-8') as f:
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

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText('选择 .docx 文件，或拖拽到此处，或手动输入路径')

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        mime: QMimeData | None = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.docx'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith('.docx'):
                    self.setText(url.toLocalFile())
                    event.acceptProposedAction()
                    return


# ---- Evidence 详情弹窗 ----

class EvidenceDialog(QDialog):
    """L4 条目 evidence 详情弹窗。"""

    def __init__(self, entry: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        word = entry.get('word', '?')
        self.setWindowTitle(f'证据链 — {word}')
        self.setMinimumSize(480, 380)
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)

        evidence: dict[str, Any] = entry.get('evidence', {})
        scoring: dict[str, Any] = evidence.get('scoring', {})
        consistency: dict[str, Any] = evidence.get('consistency', {})
        verification: dict[str, Any] = evidence.get('verification', {})
        recommendation: str = evidence.get('recommendation', '—')

        status = verification.get('status', 'pending')
        conf = verification.get('confidence', 0)

        html_parts: list[str] = [
            f'<h2>{word}</h2>',
            '<hr>',
            '<h3>评分 (Scoring)</h3>',
            '<table>',
        ]
        for k, v in sorted(scoring.items()):
            html_parts.append(f'<tr><td><b>{k}</b></td><td>{v}</td></tr>')
        html_parts.append('</table>')

        html_parts.extend([
            '<h3>一致性 (Consistency)</h3>',
            f'<p>命中: {"是" if consistency.get("hit") else "否"}'
            f' | 类型: {consistency.get("type", "—")}'
            f' | 详情: {consistency.get("detail", "—")}</p>',
            '<h3>验证 (Verification)</h3>',
            f'<p>状态: {_STATUS_LABELS.get(status, status)}'
            f' | 置信度: {conf}</p>',
            '<h3>建议动作</h3>',
            f'<p style="font-size:14px;font-weight:bold;">{recommendation}</p>',
        ])

        browser.setHtml('\n'.join(html_parts))
        layout.addWidget(browser)

        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ---- 主窗口 ----

class MainWindow(QMainWindow):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('GEHD — 文档幻觉核查工具')
        self.setMinimumSize(1100, 660)
        self.resize(1160, 740)

        self._current_stats: dict[str, int] = {}
        self._current_issues: list[str] = []
        self._current_warnings: list[str] = []
        self._current_l4_queue: list[dict[str, Any]] = []
        self._current_config: Any = None
        self._settings_dialog: Any = None
        self._verified_real_label: QLabel | None = None
        self._verified_fake_label: QLabel | None = None

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
        self._cross_validate_checkbox = QCheckBox('多模型交叉校验')
        self._cross_validate_checkbox.setToolTip(
            '三路并行检测（默认/宽松/严格），交叉比对结果'
        )
        self._scan_btn = QPushButton('扫描')
        self._scan_btn.setMinimumWidth(72)
        self._scan_btn.clicked.connect(self._scan)

        file_layout.addWidget(file_label)
        file_layout.addWidget(self._file_input, 1)
        file_layout.addWidget(self._browse_btn)
        file_layout.addWidget(self._verify_checkbox)
        file_layout.addWidget(self._cross_validate_checkbox)
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
        stats_layout.setSpacing(20)

        self._stat_labels: dict[str, QLabel] = {}
        for key in ['total_candidates', 'l25_candidates', 'high_risk',
                     'medium_risk', 'low_risk', 'l4_queue_size']:
            lbl = QLabel('—')
            lbl.setStyleSheet('border: none; background: transparent;')
            stats_layout.addWidget(lbl)
            self._stat_labels[key] = lbl

        # 动态验证统计（P2-3，存在时显示）
        self._verified_real_label = QLabel('')
        self._verified_real_label.setStyleSheet(
            'border: none; background: transparent; color: #2E7D32; font-weight: bold;'
        )
        stats_layout.addWidget(self._verified_real_label)

        self._verified_fake_label = QLabel('')
        self._verified_fake_label.setStyleSheet(
            'border: none; background: transparent; color: #C62828; font-weight: bold;'
        )
        stats_layout.addWidget(self._verified_fake_label)

        # P2-5: 交叉校验共识统计
        self._consensus_label = QLabel('')
        self._consensus_label.setStyleSheet(
            'border: none; background: transparent; color: #1B5E20; font-weight: bold;'
        )
        stats_layout.addWidget(self._consensus_label)

        # P0-2: l4_auto_verify 开关状态
        self._auto_verify_status = QLabel('')
        self._auto_verify_status.setStyleSheet(
            'border: none; background: transparent; color: #1565C0;'
        )
        stats_layout.addWidget(self._auto_verify_status)

        stats_layout.addStretch()
        layout.addWidget(self._stats_frame)

        # --- 结果标签页 ---
        self._result_tabs = QTabWidget()

        # 问题标签页
        self._issues_list = QListWidget()
        self._issues_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._issues_list.customContextMenuRequested.connect(
            lambda pos: self._on_result_context_menu(pos, self._issues_list, is_issue=True)
        )
        self._result_tabs.addTab(self._issues_list, '问题 (0)')

        # 警告标签页
        self._warnings_list = QListWidget()
        self._warnings_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._warnings_list.customContextMenuRequested.connect(
            lambda pos: self._on_result_context_menu(pos, self._warnings_list, is_issue=False)
        )
        self._result_tabs.addTab(self._warnings_list, '警告 (0)')

        # L4 验证队列标签页（表格 + 操作栏）
        self._l4_tab = QWidget()
        l4_layout = QVBoxLayout(self._l4_tab)
        l4_layout.setContentsMargins(0, 0, 0, 0)
        l4_layout.setSpacing(4)

        self._l4_table = QTableWidget()
        self._l4_table.setColumnCount(5)
        self._l4_table.setHorizontalHeaderLabels(['词', '分类', '分数', '状态', '位置'])
        self._l4_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._l4_table.customContextMenuRequested.connect(self._on_l4_context_menu)
        self._l4_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._l4_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._l4_table.horizontalHeader().setStretchLastSection(True)
        self._l4_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        # 双击行 → 查看 evidence 详情
        self._l4_table.cellDoubleClicked.connect(self._on_l4_row_double_clicked)
        l4_layout.addWidget(self._l4_table)

        # P2-4: 一键执行建议按钮
        l4_action_layout = QHBoxLayout()
        self._l4_action_btn = QPushButton('一键执行建议')
        self._l4_action_btn.setEnabled(False)
        self._l4_action_btn.clicked.connect(self._on_execute_recommendation)
        self._l4_action_label = QLabel('')
        self._l4_action_label.setStyleSheet('color: #757575;')
        l4_action_layout.addWidget(self._l4_action_btn)
        l4_action_layout.addWidget(self._l4_action_label)
        l4_action_layout.addStretch()
        l4_layout.addLayout(l4_action_layout)

        self._result_tabs.addTab(self._l4_tab, '验证队列 (0)')

        # 当切换到 L4 标签页时，更新一键执行按钮状态
        self._result_tabs.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self._result_tabs, 1)

    # ---- 状态栏 ----

    def _setup_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self._statusbar.showMessage('就绪 — 请选择一个 .docx 文件开始扫描')
        self.setStatusBar(self._statusbar)

    # ---- 浏览文件 ----

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, '选择 Word 文档', '', 'Word 文档 (*.docx);;所有文件 (*)'
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
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText('扫描中...')
        self._statusbar.showMessage('扫描中...')
        QApplication.processEvents()

        try:
            config = load_config()
            text = DocumentText.from_docx(path)
            if self._cross_validate_checkbox.isChecked():
                issues, warnings, stats, l4_queue = gehd_cross_validate(
                    text, output_verify_queue=output_l4
                )
            else:
                issues, warnings, stats, l4_queue = gehd_check(
                    text, config, output_verify_queue=output_l4
                )
        except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as e:
            self._scan_btn.setEnabled(True)
            self._scan_btn.setText('扫描')
            self._statusbar.showMessage('扫描失败')
            QMessageBox.critical(self, '扫描错误', f'扫描过程中发生错误：\n{e}')
            return

        self._current_issues = issues
        self._current_warnings = warnings
        self._current_stats = stats
        self._current_l4_queue = l4_queue
        self._current_config = config

        self._refresh_stats(stats)
        self._refresh_results(issues, warnings, l4_queue, config)

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
        # P2-5: 交叉校验时使用合并统计
        if stats.get('cross_validate_mode'):
            mapping['total_candidates'] = f'合并问题: {stats.get("merged_issues", 0)}'
            mapping['high_risk'] = f'A/B/C: {stats.get("A_issues", 0)}/{stats.get("B_issues", 0)}/{stats.get("C_issues", 0)}'
            mapping['medium_risk'] = f'A/B/C警告: {stats.get("A_warnings", 0)}/{stats.get("B_warnings", 0)}/{stats.get("C_warnings", 0)}'
            mapping['low_risk'] = ''
            mapping['l25_candidates'] = ''

        for key, label in self._stat_labels.items():
            label.setText(mapping.get(key, '—'))

        # P2-3: 动态验证统计
        vr = stats.get('l4_verified_real', 0)
        vf = stats.get('l4_verified_fake', 0)
        if self._verified_real_label:
            self._verified_real_label.setText(
                f'已验证真: {vr}' if vr > 0 else ''
            )
        if self._verified_fake_label:
            self._verified_fake_label.setText(
                f'已验证假: {vf}' if vf > 0 else ''
            )

        # P2-5: 共识统计
        strong = stats.get('cross_high_consensus', 0)
        if strong > 0:
            self._consensus_label.setText(f'强共识: {strong}')
        else:
            self._consensus_label.setText('')

        # P0-2: l4_auto_verify 状态
        cfg = self._current_config
        if cfg and getattr(cfg, 'l4_auto_verify', False):
            timeout = getattr(cfg, 'l4_search_timeout', 5.0)
            self._auto_verify_status.setText(f'联网核查: 已启用 ({timeout}s)')
        else:
            self._auto_verify_status.setText('联网核查: 已关闭')

    # ---- 结果刷新 ----

    def _refresh_results(
        self,
        issues: list[str],
        warnings: list[str],
        l4_queue: list[dict[str, Any]],
        config: Any = None,
    ) -> None:
        self._issues_list.clear()
        self._warnings_list.clear()
        self._l4_table.setRowCount(0)

        for text in issues:
            item = QListWidgetItem(text)
            item.setBackground(_COLOR_ISSUE_BG)
            item.setForeground(_COLOR_ISSUE_FG)
            item.setData(Qt.ItemDataRole.UserRole, text)
            self._issues_list.addItem(item)

        for text in warnings:
            item = QListWidgetItem(text)
            item.setBackground(_COLOR_WARNING_BG)
            item.setForeground(_COLOR_WARNING_FG)
            item.setData(Qt.ItemDataRole.UserRole, text)
            self._warnings_list.addItem(item)

        # L4 队列（5列：词/分类/分数/状态/位置）
        high_th = config.score_high_threshold if config else 65
        med_th = config.score_medium_threshold if config else 45
        self._l4_table.setRowCount(len(l4_queue))
        for row, entry in enumerate(l4_queue):
            word = entry.get('word', '')
            category = entry.get('category', '')
            score = entry.get('score', 0)
            location = entry.get('location', '')
            status = entry.get('status', 'pending')
            status_label = _STATUS_LABELS.get(status, status)

            self._l4_table.setItem(row, 0, QTableWidgetItem(word))
            self._l4_table.setItem(row, 1, QTableWidgetItem(category))

            score_item = QTableWidgetItem()
            score_item.setData(Qt.ItemDataRole.DisplayRole, score)
            self._l4_table.setItem(row, 2, score_item)

            status_item = QTableWidgetItem(status_label)
            self._l4_table.setItem(row, 3, status_item)

            self._l4_table.setItem(row, 4, QTableWidgetItem(location))

            # P2-3: 按验证状态着色（优先于分数阈值着色）
            status_colors = self._get_status_colors(status)
            # P2-5: 交叉校验共识级别
            xv = entry.get('cross_validation', {})
            consensus = xv.get('consensus_level', '')
            consensus_colors = self._get_consensus_colors(consensus)

            if status_colors:
                for col in range(5):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(status_colors[0])
                        if col == 3:
                            cell.setForeground(status_colors[1])
            elif consensus_colors:
                for col in range(5):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(consensus_colors[0])
            elif score >= high_th:
                for col in range(5):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(_COLOR_L4_HIGH_BG)
            elif score >= med_th:
                for col in range(5):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(_COLOR_L4_MED_BG)

        self._result_tabs.setTabText(0, f'问题 ({len(issues)})')
        self._result_tabs.setTabText(1, f'警告 ({len(warnings)})')
        self._result_tabs.setTabText(2, f'验证队列 ({len(l4_queue)})')

        # 更新一键执行按钮
        self._update_action_button()

    @staticmethod
    def _get_status_colors(status: str) -> tuple[QColor, QColor] | None:
        """返回 (bg, fg) 或 None（无特殊颜色）。"""
        if status == 'verified_real':
            return (_COLOR_VERIFIED_REAL_BG, _COLOR_VERIFIED_REAL_FG)
        if status == 'verified_fake':
            return (_COLOR_VERIFIED_FAKE_BG, _COLOR_VERIFIED_FAKE_FG)
        if status == 'need_manual_check':
            return (_COLOR_NEED_MANUAL_BG, _COLOR_NEED_MANUAL_FG)
        if status == 'unable_to_verify':
            return (_COLOR_UNABLE_BG, _COLOR_UNABLE_FG)
        return None

    @staticmethod
    def _get_consensus_colors(level: str) -> tuple[QColor, QColor] | None:
        """返回 (bg, fg) 或 None。"""
        if level == 'strong':
            return (_COLOR_STRONG_CONSENSUS_BG, QColor('#1B5E20'))
        if level == 'weak':
            return (_COLOR_WEAK_CONSENSUS_BG, QColor('#33691E'))
        if level == 'divergent':
            return (_COLOR_DIVERGENT_BG, QColor('#757575'))
        return None

    # ---- L4 行双击 → evidence 详情 ----

    def _on_l4_row_double_clicked(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._current_l4_queue):
            return
        entry = self._current_l4_queue[row]
        dialog = EvidenceDialog(entry, self)
        dialog.exec()

    # ---- 一键执行建议 ----

    def _on_tab_changed(self, index: int) -> None:
        if index == 2:
            self._update_action_button()

    def _on_l4_table_selection_changed(self) -> None:
        self._update_action_button()

    def _update_action_button(self) -> None:
        row = self._l4_table.currentRow()
        if row < 0:
            self._l4_action_btn.setEnabled(False)
            self._l4_action_label.setText('')
            return

        entry: dict[str, Any] = self._current_l4_queue[row]
        evidence: dict[str, Any] = entry.get('evidence', {})
        recommendation: str = evidence.get('recommendation', '')

        # 仅对可执行建议启用
        actionable = {'建议加白名单', '建议加黑名单'}
        if recommendation in actionable:
            self._l4_action_btn.setEnabled(True)
            self._l4_action_label.setText(recommendation)
        else:
            self._l4_action_btn.setEnabled(False)
            self._l4_action_label.setText(recommendation or '')

    def _on_execute_recommendation(self) -> None:
        row = self._l4_table.currentRow()
        if row < 0 or row >= len(self._current_l4_queue):
            return
        entry = self._current_l4_queue[row]
        word = entry.get('word', '')
        evidence: dict[str, Any] = entry.get('evidence', {})
        recommendation: str = evidence.get('recommendation', '')

        if recommendation == '建议加白名单':
            action = 'real'
        elif recommendation == '建议加黑名单':
            action = 'fake'
        else:
            return

        if action == 'real':
            target_file = _CONFIG_DIR / 'whitelist.json'
            target_key = 'whitelist'
            action_name = '白名单'
        else:
            target_file = _CONFIG_DIR / 'blacklist.json'
            target_key = 'blacklist'
            action_name = '黑名单'

        if _word_in_json_array(target_file, target_key, word):
            QMessageBox.information(self, '已存在', f'"{word}" 已在{action_name}中。')
            return

        try:
            _append_to_json_array(target_file, target_key, word)
        except OSError as e:
            QMessageBox.warning(self, '写入失败', f'写入配置文件时出错：{e}')
            return

        self._l4_table.removeRow(row)
        self._result_tabs.setTabText(2, f'验证队列 ({self._l4_table.rowCount()})')
        self._update_action_button()
        self._statusbar.showMessage(f'已执行：{recommendation} — "{word}"')

    # ---- 右键菜单：问题/警告列表 ----

    def _on_result_context_menu(
        self, pos, list_widget: QListWidget, is_issue: bool,
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
        if row < 0 or row >= len(self._current_l4_queue):
            return
        word_item = self._l4_table.item(row, 0)
        if not word_item:
            return
        word = word_item.text()
        self._show_context_menu(pos, self._l4_table, word, row=row)

    # ---- 右键菜单核心 ----

    def _show_context_menu(
        self, pos, widget: QListWidget | QTableWidget, word: str,
        item: QListWidgetItem | None = None, *, row: int = -1,
    ) -> None:
        menu = QMenu(self)

        # P2-4: 根据验证状态禁用对应菜单项
        real_enabled = True
        fake_enabled = True
        if isinstance(widget, QTableWidget) and 0 <= row < len(self._current_l4_queue):
            entry_status = self._current_l4_queue[row].get('status', 'pending')
            if entry_status == 'verified_real':
                real_enabled = False
            elif entry_status == 'verified_fake':
                fake_enabled = False

        if real_enabled:
            real_action = QAction('确认真实', self)
            real_action.triggered.connect(
                lambda: self._mark_word(word, 'real', widget, item, row)
            )
            menu.addAction(real_action)

        if fake_enabled:
            fake_action = QAction('确认幻觉', self)
            fake_action.triggered.connect(
                lambda: self._mark_word(word, 'fake', widget, item, row)
            )
            menu.addAction(fake_action)

        if not real_enabled and not fake_enabled:
            info_action = QAction('（已确认，无需操作）', self)
            info_action.setEnabled(False)
            menu.addAction(info_action)

        menu.exec(widget.viewport().mapToGlobal(pos))

    def _mark_word(
        self, word: str, action: str, widget: QListWidget | QTableWidget,
        item: QListWidgetItem | None, row: int,
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
            self._update_action_button()

    # ---- 设置窗口 ----

    def _open_settings(self) -> None:
        if (hasattr(self, '_settings_dialog')
                and self._settings_dialog is not None
                and self._settings_dialog.isVisible()):
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        from hallucination_checker.gui.settings_dialog import SettingsDialog
        self._settings_dialog = SettingsDialog(self)
        self._settings_dialog.setWindowModality(Qt.WindowModality.NonModal)
        self._settings_dialog.show()


# ---- 入口 ----

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName('GEHD')
    app.setApplicationVersion(GEHD_VERSION)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
