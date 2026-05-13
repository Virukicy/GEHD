"""GEHD GUI 主窗口 — PySide6 桌面应用。v0.3.1 主题系统。

功能：
  - 加载文档（9 种格式）
  - 触发异步扫描（gehd_check / gehd_cross_validate）
  - 四标签页：问题 / 警告 / 验证队列 / 文档视图
  - 右键标记候选词 / 一键执行建议
  - 主题切换（默认/深夜/色盲友好）
  - 全文高亮视图 + 证据链弹窗
"""
from __future__ import annotations

import html as _html
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

from PySide6.QtCore import QMimeData, Qt, QThread, Signal
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

from hallucination_checker.engine.config import GEHD_VERSION, load_config
from hallucination_checker.engine.cross_validate import gehd_cross_validate
from hallucination_checker.gui.settings_dialog import get_config_dir
from hallucination_checker.gui.theme import Theme
from hallucination_checker.io.document_text import DocumentText

_CONFIG_DIR = get_config_dir()

# ---- 多格式支持 ----
_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    '.docx', '.txt', '.md', '.html', '.htm', '.jsonl', '.csv', '.pdf', '.pptx',
})
_FACTORY_MAP: dict[str, Any] = {
    '.docx': DocumentText.from_docx,
    '.txt':  DocumentText.from_text,
    '.md':   DocumentText.from_markdown,
    '.html': DocumentText.from_html,
    '.htm':  DocumentText.from_html,
    '.jsonl': DocumentText.from_jsonl,
    '.csv':  DocumentText.from_csv,
    '.pdf':  DocumentText.from_pdf,
    '.pptx': DocumentText.from_pptx,
}

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
        _atomic_json_write(filepath, data)


def _atomic_json_write(filepath: Path, data: dict[str, Any]) -> None:
    """原子写入 JSON：先写临时文件，再 os.replace 交换。"""
    fd, tmp_name = tempfile.mkstemp(suffix='.tmp', dir=str(filepath.parent), prefix='gehd_')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_name, filepath)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


# ---- 主题持久化 ----
_SETTINGS_PATH = Path(__file__).resolve().parents[5] / 'workspace' / 'U' / 'settings.json'


def _load_theme_name() -> str:
    try:
        with open(_SETTINGS_PATH, encoding='utf-8') as f:
            data: Any = json.load(f)
        return str(data.get('theme', 'default'))
    except (FileNotFoundError, json.JSONDecodeError):
        return 'default'


def _save_theme_name(name: str) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if _SETTINGS_PATH.exists():
        try:
            with open(_SETTINGS_PATH, encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    data['theme'] = name
    with open(_SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---- 拖拽支持 ----

class DropLineEdit(QLineEdit):

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setPlaceholderText('选择文件，或拖拽到此处，或手动输入路径 (.docx/.pdf/.txt/.md/.html/.jsonl/.csv/.pptx)')

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # noqa: N802
        mime: QMimeData | None = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(tuple(_SUPPORTED_EXTENSIONS)):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # noqa: N802
        mime = event.mimeData()
        if mime and mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile() and url.toLocalFile().lower().endswith(tuple(_SUPPORTED_EXTENSIONS)):
                    self.setText(url.toLocalFile())
                    event.acceptProposedAction()
                    return


# ---- Evidence 详情弹窗 ----

class EvidenceDialog(QDialog):

    def __init__(self, entry: dict[str, Any], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        word = entry.get('word', '?')
        self.setWindowTitle(f'证据链 — {word}')
        safe_word = _html.escape(word)
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
            f'<h2>{safe_word}</h2>', '<hr>',
            '<h3>评分 (Scoring)</h3>', '<table>',
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


# ---- 决策追溯弹窗 ----

class DecisionTraceDialog(QDialog):
    """从 PipelineContext.decision_log 渲染决策链。"""

    def __init__(self, decision_log: list[dict[str, Any]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('决策追溯链')
        self.setMinimumSize(560, 420)
        self.resize(600, 480)

        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)

        if not decision_log:
            browser.setHtml('<p style="color:#999;">无决策记录。</p>')
        else:
            rows: list[str] = ['<h2>决策追溯链</h2>', '<hr>']
            for i, entry in enumerate(decision_log):
                stage = entry.get('stage', f'阶段{i+1}')
                status = entry.get('status', '?')
                reason = entry.get('reason', '')
                ts = entry.get('timestamp', '')[:19]
                result = entry.get('result', {})

                status_icon = {'completed': '✅', 'skipped': '⏭️', 'warning': '⚠️', 'error': '❌'}.get(status, '❓')
                rows.append(
                    f'<h3>{status_icon} [{stage}] {status}</h3>'
                )
                if reason:
                    rows.append(f'<p><b>原因:</b> {_html.escape(reason)}</p>')
                if result and status == 'completed':
                    rows.append('<p><b>结果:</b></p><ul>')
                    for k, v in result.items():
                        rows.append(f'<li>{_html.escape(str(k))}: {_html.escape(str(v))}</li>')
                    rows.append('</ul>')
                if ts and ts > '0001':
                    rows.append(f'<p style="color:#999;font-size:12px;">{ts}</p>')
                if i < len(decision_log) - 1:
                    rows.append('<hr>')
            browser.setHtml('\n'.join(rows))

        layout.addWidget(browser)
        close_btn = QPushButton('关闭')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ---- 后台扫描线程 ----

class ScanWorker(QThread):
    finished = Signal(dict)
    error_msg = Signal(str)
    progress = Signal(str)

    def __init__(
        self, text: DocumentText, config: Any, output_l4: bool,
        cross_validate: bool, parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._config = config
        self._output_l4 = output_l4
        self._cross_validate = cross_validate

    @staticmethod
    def _create_llm():
        """根据 pipeline.json 创建 LLM 适配器，None 则纯规则。"""
        try:
            from hallucination_checker.engine.llm.adapter import create_llm_adapter_from_config
            return create_llm_adapter_from_config()
        except Exception:
            return None

    def run(self) -> None:
        try:
            if self._cross_validate:
                self.progress.emit('三路并行交叉校验中...')
                issues, warnings, stats, l4_queue = gehd_cross_validate(
                    self._text, output_verify_queue=self._output_l4
                )
                context: dict[str, Any] = {}
            else:
                from hallucination_checker.engine.pipeline import run_pipeline
                self.progress.emit('规则引擎...')
                ctx = run_pipeline(
                    self._text, self._config,
                    llm=self._create_llm(),
                    output_verify_queue=self._output_l4,
                    progress_callback=lambda stage: self.progress.emit(f'{stage}...'),
                )
                issues = ctx['issues']
                warnings = ctx['warnings']
                stats = ctx['stats']
                l4_queue = ctx['l4_queue']
                context = dict(ctx)
            self.finished.emit({
                'issues': issues, 'warnings': warnings,
                'stats': stats, 'l4_queue': l4_queue, 'config': self._config,
                'context': context,
            })
        except Exception as e:
            self.error_msg.emit(str(e))


# ---- 主窗口 ----

class MainWindow(QMainWindow):

    def __init__(self, theme: Theme | None = None) -> None:
        super().__init__()
        self.setWindowTitle('GEHD — 文档幻觉核查工具')
        self.setMinimumSize(1100, 660)
        self.resize(1160, 740)

        # 主题
        self.theme: Theme = theme or Theme.default()
        self._apply_theme()

        # 状态
        self._current_stats: dict[str, int] = {}
        self._current_issues: list[str] = []
        self._current_warnings: list[str] = []
        self._current_l4_queue: list[dict[str, Any]] = []
        self._current_config: Any = None
        self._current_text: Any = None
        self._current_context: dict[str, Any] | None = None
        self._settings_dialog: Any = None
        self._verified_real_label: QLabel | None = None
        self._verified_fake_label: QLabel | None = None

        self._setup_menu()
        self._setup_ui()
        self._setup_legend()
        self._setup_statusbar()
        self._refresh_widget_theme()

    # ---- 主题 ----

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            app.setStyleSheet(self.theme.stylesheet())

    def set_theme(self, theme: Theme) -> None:
        self.theme = theme
        self._apply_theme()
        _save_theme_name(theme.dir_name())
        self._refresh_widget_theme()
        self._rebuild_legend()
        self._refresh_document_view()

    def _refresh_widget_theme(self) -> None:
        """将主题令牌应用到所有硬编码样式的控件。"""
        card = self.theme.color('surface.card')
        border = self.theme.color('surface.border')
        text_primary = self.theme.color('text.primary')
        text_secondary = self.theme.color('text.secondary')
        verified_fg = self.theme.color('severity.verified.fg')
        issue_fg = self.theme.color('severity.issue.fg')
        consensus_fg = self.theme.color('severity.consensus_strong.fg')
        link_color = self.theme.color('text.link')

        # 统计条背景
        self._stats_frame.setStyleSheet(
            f'QFrame {{ background-color: {card.name()}; border: 1px solid {border.name()}; '
            'border-radius: 4px; padding: 6px 10px; }'
        )

        # 统计条内标签
        for key_label in self._stat_labels.values():
            key_label.setStyleSheet(
                f'border: none; background: transparent; color: {text_primary.name()};'
            )

        # 验证/共识/核查 标签
        if self._verified_real_label:
            self._verified_real_label.setStyleSheet(
                f'border: none; background: transparent; color: {verified_fg.name()}; font-weight: bold;'
            )
        if self._verified_fake_label:
            self._verified_fake_label.setStyleSheet(
                f'border: none; background: transparent; color: {issue_fg.name()}; font-weight: bold;'
            )
        if self._consensus_label:
            self._consensus_label.setStyleSheet(
                f'border: none; background: transparent; color: {consensus_fg.name()}; font-weight: bold;'
            )
        if self._auto_verify_status:
            self._auto_verify_status.setStyleSheet(
                f'border: none; background: transparent; color: {link_color.name()};'
            )

        # 操作栏标签
        self._l4_action_label.setStyleSheet(f'color: {text_secondary.name()};')

        # 图例条文字
        for _swatch, label_widget in self._legend_items:
            label_widget.setStyleSheet(
                f'border: none; background: transparent; font-size: 11px; color: {text_secondary.name()};'
            )

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

        # 文件选择行
        file_layout = QHBoxLayout()
        file_layout.setSpacing(6)
        file_label = QLabel('文件路径：')
        self._file_input = DropLineEdit()
        self._file_input.setMinimumWidth(320)
        self._browse_btn = QPushButton('浏览')
        self._browse_btn.clicked.connect(self._browse_file)
        self._verify_checkbox = QCheckBox('生成验证队列')
        self._cross_validate_checkbox = QCheckBox('多模型交叉校验')
        self._cross_validate_checkbox.setToolTip('三路并行检测（默认/宽松/严格），交叉比对结果')
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

        # 统计条
        self._stats_frame = QFrame()
        self._stats_frame.setFrameShape(QFrame.Shape.StyledPanel)

        stats_layout = QHBoxLayout(self._stats_frame)
        stats_layout.setContentsMargins(12, 4, 12, 4)
        stats_layout.setSpacing(20)

        self._stat_labels: dict[str, QLabel] = {}
        for key in ['total_candidates', 'l25_candidates', 'high_risk',
                     'medium_risk', 'low_risk', 'l4_queue_size']:
            lbl = QLabel('—')
            stats_layout.addWidget(lbl)
            self._stat_labels[key] = lbl

        self._verified_real_label = QLabel('')
        stats_layout.addWidget(self._verified_real_label)

        self._verified_fake_label = QLabel('')
        stats_layout.addWidget(self._verified_fake_label)

        self._consensus_label = QLabel('')
        stats_layout.addWidget(self._consensus_label)

        self._auto_verify_status = QLabel('')
        stats_layout.addWidget(self._auto_verify_status)

        stats_layout.addStretch()
        layout.addWidget(self._stats_frame)

        # 存储需要主题刷新的 stats 标签引用
        self._stats_themed_widgets: list[tuple[QFrame, QLabel, QLabel, QLabel, QLabel]] = [
            (self._stats_frame, self._verified_real_label, self._verified_fake_label,
             self._consensus_label, self._auto_verify_status),
        ]

        # 结果标签页
        self._result_tabs = QTabWidget()

        self._issues_list = QListWidget()
        self._issues_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._issues_list.customContextMenuRequested.connect(
            lambda pos: self._on_result_context_menu(pos, self._issues_list, is_issue=True)
        )
        self._result_tabs.addTab(self._issues_list, '问题 (0)')

        self._warnings_list = QListWidget()
        self._warnings_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._warnings_list.customContextMenuRequested.connect(
            lambda pos: self._on_result_context_menu(pos, self._warnings_list, is_issue=False)
        )
        self._result_tabs.addTab(self._warnings_list, '警告 (0)')

        # L4 验证队列
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
        self._l4_table.cellDoubleClicked.connect(self._on_l4_row_double_clicked)
        l4_layout.addWidget(self._l4_table)

        l4_action_layout = QHBoxLayout()
        self._l4_action_btn = QPushButton('一键执行建议')
        self._l4_action_btn.setEnabled(False)
        self._l4_action_btn.clicked.connect(self._on_execute_recommendation)
        self._l4_action_label = QLabel('')
        self._l4_action_label.setObjectName('l4_action_label')
        l4_action_layout.addWidget(self._l4_action_btn)
        l4_action_layout.addWidget(self._l4_action_label)
        l4_action_layout.addStretch()
        l4_layout.addLayout(l4_action_layout)

        self._result_tabs.addTab(self._l4_tab, '验证队列 (0)')

        # 文档视图
        self._doc_view = QTextBrowser()
        self._doc_view.setOpenExternalLinks(False)
        self._doc_view.setReadOnly(True)
        self._result_tabs.addTab(self._doc_view, '文档视图')

        self._result_tabs.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self._result_tabs, 1)

    # ---- 图例条 ----

    def _setup_legend(self) -> None:
        card_color = self.theme.color('surface.card')
        self._legend = QFrame()
        self._legend.setStyleSheet(
            f'QFrame {{ background: {card_color.name()}; border: 1px solid '
            + self.theme.color('surface.border').name() + '; border-radius: 4px; padding: 4px 12px; }}'
        )
        legend_layout = QHBoxLayout(self._legend)
        legend_layout.setContentsMargins(8, 2, 8, 2)
        legend_layout.setSpacing(16)
        self._legend_items: list[tuple[QLabel, QLabel]] = []
        for token_key, label in [
            ('severity.issue', '高危'),
            ('severity.warning', '中危'),
            ('severity.low', '低危'),
            ('severity.verified', '已验证'),
            ('severity.uncertain', '无法验证'),
            ('severity.declaration', '声明'),
        ]:
            swatch = QLabel('  ')
            swatch.setFixedSize(18, 18)
            swatch.setStyleSheet(
                f'background-color: {self.theme.color(token_key + ".bg").name()}; '
                'border-radius: 2px; border: 1px solid #CCC;'
            )
            text = QLabel(label)
            text.setObjectName('legend_label')
            legend_layout.addWidget(swatch)
            legend_layout.addWidget(text)
            self._legend_items.append((swatch, text))
        legend_layout.addStretch()
        central = self.centralWidget()
        layout = central.layout()
        if layout is not None:
            layout.addWidget(self._legend)

        # 管道状态栏
        card = self.theme.color('surface.card').name()
        border = self.theme.color('surface.border').name()
        text_secondary = self.theme.color('text.secondary').name()
        self._pipeline_bar = QLabel('管道: 规则引擎（本地）')
        self._pipeline_bar.setStyleSheet(
            f'border: 1px solid {border}; background: {card}; border-radius: 4px; '
            f'padding: 4px 12px; font-size: 11px; color: {text_secondary};'
        )
        if layout is not None:
            layout.addWidget(self._pipeline_bar)

    def _refresh_pipeline_status(self) -> None:
        """根据 PipelineContext.status 刷新管道状态栏。"""
        ctx = self._current_context
        if ctx:
            dl = ctx.get('decision_log', [])
            # 从 decision_log 中提取实际执行的阶段
            stages_done: list[str] = []
            for entry in dl:
                stage = entry.get('stage', '')
                if stage and entry.get('status') == 'completed' and stage not in stages_done:
                    stages_done.append(stage)
            if stages_done:
                stage_labels = {
                    'rules': '规则', 'llm_pre': 'LLM前置', 'web_verify': '联网核查',
                    'llm_post': 'LLM后置', 'llm_direct': 'LLM直验',
                    'cross_validate': '交叉校验', 'output_queue': '验证队列',
                }
                parts = ['管道:'] + [stage_labels.get(s, s) for s in stages_done]
                self._pipeline_bar.setText(' → '.join(parts))
                return

        # 无 context 时回退读 pipeline.json
        try:
            import json
            path = _CONFIG_DIR / 'pipeline.json'
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
            mode = data.get('mode', 'full')
            mode_labels = {'full': '全链路', 'fast': '仅规则引擎', 'offline': '离线'}
            self._pipeline_bar.setText(f'管道: {mode_labels.get(mode, mode)}')
        except (FileNotFoundError, json.JSONDecodeError):
            self._pipeline_bar.setText('管道: 规则引擎（本地）')

    def _rebuild_legend(self) -> None:
        for i, (token_key, _label) in enumerate([
            ('severity.issue', '高危'),
            ('severity.warning', '中危'),
            ('severity.low', '低危'),
            ('severity.verified', '已验证'),
            ('severity.uncertain', '无法验证'),
            ('severity.declaration', '声明'),
        ]):
            if i < len(self._legend_items):
                self._legend_items[i][0].setStyleSheet(
                        f'background-color: {self.theme.color(token_key + ".bg").name()}; '
                        'border-radius: 2px; border: 1px solid #CCC;'
                    )
        card_color = self.theme.color('surface.card')
        border_color = self.theme.color('surface.border')
        self._legend.setStyleSheet(
            f'QFrame {{ background: {card_color.name()}; border: 1px solid '
            f'{border_color.name()}; border-radius: 4px; padding: 4px 12px; }}'
        )

    # ---- 状态栏 ----

    def _setup_statusbar(self) -> None:
        self._statusbar = QStatusBar()
        self._statusbar.showMessage('就绪 — 请选择一个文件开始扫描')
        self.setStatusBar(self._statusbar)

    # ---- 浏览 ----

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, '选择文档', '',
            '文档文件 (*.docx *.pdf *.pptx *.txt *.md *.html *.jsonl *.csv);;所有文件 (*)',
        )
        if path:
            self._file_input.setText(path)

    # ---- 扫描 ----

    def _scan(self) -> None:
        filepath = self._file_input.text().strip()
        if not filepath:
            QMessageBox.warning(self, '缺少文件', '请先选择或输入一个文档文件路径。')
            return
        path = Path(filepath)
        if not path.exists():
            QMessageBox.warning(self, '文件不存在', f'找不到文件：\n{filepath}')
            return

        ext = path.suffix.lower()
        factory = _FACTORY_MAP.get(ext)
        if factory is None:
            QMessageBox.warning(
                self, '格式不支持',
                f'不支持的格式（{ext}）。\n支持：.docx .pdf .pptx .txt .md .html .jsonl .csv'
            )
            return

        output_l4 = self._verify_checkbox.isChecked()
        cross_validate = self._cross_validate_checkbox.isChecked()

        try:
            config = load_config()
            text = factory(path)
        except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as e:
            QMessageBox.critical(self, '加载失败', f'无法加载文档：\n{e}')
            return

        self._scan_btn.setEnabled(False)
        self._scan_btn.setText('扫描中...')
        self._statusbar.showMessage('扫描中...')

        self._current_text = text

        self._worker = ScanWorker(text, config, output_l4, cross_validate, self)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error_msg.connect(self._on_scan_error)
        self._worker.progress.connect(self._statusbar.showMessage)
        self._worker.start()

    def _on_scan_finished(self, result: dict[str, Any]) -> None:
        issues: list[str] = result['issues']
        warnings: list[str] = result['warnings']
        stats: dict[str, int] = result['stats']
        l4_queue: list[dict[str, Any]] = result['l4_queue']
        config: Any = result['config']

        self._current_issues = issues
        self._current_warnings = warnings
        self._current_stats = stats
        self._current_l4_queue = l4_queue
        self._current_config = config
        self._current_context = result.get('context')

        self._refresh_stats(stats)
        self._refresh_results(issues, warnings, l4_queue, config)
        self._refresh_document_view()

        self._scan_btn.setEnabled(True)
        self._scan_btn.setText('重新扫描')
        self._refresh_pipeline_status()
        issue_count = len(issues)
        self._statusbar.showMessage(
            f'扫描完成，发现 {issue_count} 个问题' if issue_count > 0 else '扫描完成，未发现问题'
        )

    def _on_scan_error(self, error: str) -> None:
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText('扫描')
        self._statusbar.showMessage('扫描失败')
        QMessageBox.critical(self, '扫描错误', f'扫描过程中发生错误：\n{error}')

    # ---- 统计条 ----

    def _refresh_stats(self, stats: dict[str, int]) -> None:
        mapping: dict[str, str] = {
            'total_candidates':   f'候选实体: {stats.get("total_candidates", 0)}',
            'l25_candidates':     f'L2.5候选: {stats.get("l25_candidates", 0)}',
            'high_risk':          f'高危: {stats.get("high_risk", 0)}',
            'medium_risk':        f'中危: {stats.get("medium_risk", 0)}',
            'low_risk':           f'低危: {stats.get("low_risk", 0)}',
            'l4_queue_size':      f'L4队列: {stats.get("l4_queue_size", 0)}',
        }
        if stats.get('cross_validate_mode'):
            mapping['total_candidates'] = f'合并问题: {stats.get("merged_issues", 0)}'
            mapping['high_risk'] = f'A/B/C: {stats.get("A_issues", 0)}/{stats.get("B_issues", 0)}/{stats.get("C_issues", 0)}'
            mapping['medium_risk'] = f'A/B/C警告: {stats.get("A_warnings", 0)}/{stats.get("B_warnings", 0)}/{stats.get("C_warnings", 0)}'
            mapping['low_risk'] = ''
            mapping['l25_candidates'] = ''

        for key, label in self._stat_labels.items():
            label.setText(mapping.get(key, '—'))

        vr = stats.get('l4_verified_real', 0)
        vf = stats.get('l4_verified_fake', 0)
        if self._verified_real_label:
            self._verified_real_label.setText(f'已验证真: {vr}' if vr > 0 else '')
        if self._verified_fake_label:
            self._verified_fake_label.setText(f'已验证假: {vf}' if vf > 0 else '')

        strong = stats.get('cross_high_consensus', 0)
        self._consensus_label.setText(f'强共识: {strong}' if strong > 0 else '')

        cfg = self._current_config
        if cfg and getattr(cfg, 'l4_auto_verify', False):
            timeout = getattr(cfg, 'l4_search_timeout', 5.0)
            self._auto_verify_status.setText(f'联网核查: 已启用 ({timeout}s)')
        else:
            self._auto_verify_status.setText('联网核查: 已关闭')

    # ---- 结果刷新 ----

    def _refresh_results(
        self, issues: list[str], warnings: list[str],
        l4_queue: list[dict[str, Any]], config: Any = None,
    ) -> None:
        self._issues_list.clear()
        self._warnings_list.clear()
        self._l4_table.setRowCount(0)

        issue_bg = self.theme.color('severity.issue.bg')
        issue_fg = self.theme.color('severity.issue.fg')
        warn_bg = self.theme.color('severity.warning.bg')
        warn_fg = self.theme.color('severity.warning.fg')

        for text in issues:
            item = QListWidgetItem(text)
            item.setBackground(issue_bg)
            item.setForeground(issue_fg)
            item.setData(Qt.ItemDataRole.UserRole, text)
            self._issues_list.addItem(item)

        for text in warnings:
            item = QListWidgetItem(text)
            item.setBackground(warn_bg)
            item.setForeground(warn_fg)
            item.setData(Qt.ItemDataRole.UserRole, text)
            self._warnings_list.addItem(item)

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

            status_colors = self._get_status_colors(status)
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
                        cell.setBackground(self.theme.color('severity.issue.bg'))
            elif score >= med_th:
                for col in range(5):
                    cell = self._l4_table.item(row, col)
                    if cell:
                        cell.setBackground(self.theme.color('severity.warning.bg'))

        self._result_tabs.setTabText(0, f'问题 ({len(issues)})')
        self._result_tabs.setTabText(1, f'警告 ({len(warnings)})')
        self._result_tabs.setTabText(2, f'验证队列 ({len(l4_queue)})')
        self._update_action_button()

    def _get_status_colors(self, status: str) -> tuple[QColor, QColor] | None:
        if status == 'verified_real':
            return (self.theme.color('severity.verified.bg'), self.theme.color('severity.verified.fg'))
        if status == 'verified_fake':
            return (self.theme.color('severity.issue.bg'), self.theme.color('severity.issue.fg'))
        if status == 'need_manual_check':
            return (self.theme.color('severity.warning.bg'), self.theme.color('severity.warning.fg'))
        if status == 'unable_to_verify':
            return (self.theme.color('severity.uncertain.bg'), self.theme.color('severity.uncertain.fg'))
        return None

    def _get_consensus_colors(self, level: str) -> tuple[QColor, QColor] | None:
        if level == 'strong':
            return (self.theme.color('severity.consensus_strong.bg'), self.theme.color('severity.consensus_strong.fg'))
        if level == 'weak':
            return (self.theme.color('severity.consensus_weak.bg'), self.theme.color('severity.consensus_weak.fg'))
        if level == 'divergent':
            return (self.theme.color('severity.uncertain.bg'), self.theme.color('severity.uncertain.fg'))
        return None

    # ---- L4 双击 → evidence ----

    def _on_l4_row_double_clicked(self, row: int, _col: int) -> None:
        if row < 0 or row >= len(self._current_l4_queue):
            return
        dialog = EvidenceDialog(self._current_l4_queue[row], self)
        dialog.exec()

    # ---- 一键执行建议 ----

    def _on_tab_changed(self, index: int) -> None:
        if index == 2:
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

    # ---- 文档视图 ----

    def _refresh_document_view(self) -> None:
        text = self._current_text
        if text is None:
            self._doc_view.setHtml(
                f'<p style="color:{self.theme.color("text.secondary").name()};">请先扫描文档。</p>'
            )
            return

        highlights: dict[str, list[tuple[str, str]]] = {}
        secondary = self.theme.color('text.secondary').name()
        card = self.theme.color('surface.card').name()

        for issue in self._current_issues:
            loc, word = self._parse_location_word(issue)
            if loc:
                highlights.setdefault(loc, []).append((word, 'issue'))

        for warning in self._current_warnings:
            loc, word = self._parse_location_word(warning)
            if loc:
                highlights.setdefault(loc, []).append((word, 'warning'))

        for entry in self._current_l4_queue:
            loc = entry.get('location', '')
            word = entry.get('word', '')
            status = entry.get('status', 'pending')
            if loc and word:
                sev = 'verified_real' if status == 'verified_real' else 'l4_pending'
                highlights.setdefault(loc, []).append((word, sev))

        parts_html: list[str] = []
        for part in text.parts:
            loc = part.location
            part_text = part.text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            display_label = part.display

            loc_highlights = highlights.get(loc, [])
            if loc_highlights:
                for word, severity in sorted(loc_highlights, key=lambda x: -len(x[0])):
                    css_class, title_attr = {
                        'issue': ('hl-issue', '高危'),
                        'warning': ('hl-warning', '中危'),
                        'verified_real': ('hl-real', '已验证真'),
                        'l4_pending': ('hl-l4', '待验证'),
                    }.get(severity, ('hl-info', ''))
                    escaped = word.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    if escaped in part_text:
                        part_text = part_text.replace(
                            escaped,
                            f'<span class="{css_class}" title="{title_attr}">{escaped}</span>',
                            1
                        )

            loc_tag = f' <small style="color:{secondary};">[{display_label}]</small>'
            parts_html.append(f'<p><span class="loc-label">{loc_tag}</span>{part_text}</p>')

        body = '\n'.join(parts_html) if parts_html else f'<p style="color:{secondary};">无内容</p>'

        # 用主题令牌颜色生成 CSS
        css_parts: list[str] = []
        for cls_name, token_key in [
            ('hl-issue', 'severity.issue.bg'),
            ('hl-warning', 'severity.warning.bg'),
            ('hl-real', 'severity.verified.bg'),
            ('hl-l4', 'severity.declaration.bg'),
            ('hl-info', 'severity.uncertain.bg'),
        ]:
            css_parts.append(f'.{cls_name} {{ background-color: {self.theme.color(token_key).name()}; '
                             'padding: 1px 3px; border-radius: 2px; cursor: pointer; }}')

        html = f'''<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, sans-serif; font-size: 14px; line-height: 1.8; margin: 24px; color: {self.theme.color("text.primary").name()}; background: {self.theme.color("surface.background").name()}; }}
  .loc-label {{ color: {secondary}; font-size: 12px; margin-right: 8px; }}
  .hl-real {{ text-decoration: line-through; }}
{chr(10).join(css_parts)}
  .stats-bar {{ margin-bottom: 16px; padding: 8px 12px; background: {card}; border-radius: 4px; font-size: 13px; }}
</style></head><body>
<div class="stats-bar">
  问题: {len(self._current_issues)} | 警告: {len(self._current_warnings)} | 候选: {len(self._current_l4_queue)} | 段落: {len(text.parts)}
</div>
{body}
</body></html>'''
        self._doc_view.setHtml(html)

    @staticmethod
    def _parse_location_word(text: str) -> tuple[str, str]:
        import re as _re
        loc_m = _re.search(r'\b(P\d+|T\d+\[\d+,\d+\])\b', text)
        location = loc_m.group(1) if loc_m else ''
        word_m = _re.search(r'["\u201c]([^"\u201d]+)["\u201d]', text)
        if not word_m:
            word_m = _re.search(r"'([^']+)'", text)
        keyword = word_m.group(1) if word_m else ''
        return location, keyword

    # ---- 右键菜单 ----

    def _on_result_context_menu(self, pos, list_widget: QListWidget, is_issue: bool) -> None:
        item = list_widget.currentItem()
        if not item:
            return
        text = item.data(Qt.ItemDataRole.UserRole) or item.text()
        word = _extract_word_from_issue(text)
        self._show_context_menu(pos, list_widget, word, item)

    def _on_l4_context_menu(self, pos) -> None:
        row = self._l4_table.currentRow()
        if row < 0 or row >= len(self._current_l4_queue):
            return
        word_item = self._l4_table.item(row, 0)
        if not word_item:
            return
        word = word_item.text()
        self._show_context_menu(pos, self._l4_table, word, row=row)

    def _show_context_menu(
        self, pos, widget: QListWidget | QTableWidget, word: str,
        item: QListWidgetItem | None = None, *, row: int = -1,
    ) -> None:
        menu = QMenu(self)

        # 查看决策链（v0.5.0 审计视图）
        if self._current_context and self._current_context.get('decision_log'):
            audit_action = QAction('查看决策链', self)
            audit_action.triggered.connect(
                lambda: DecisionTraceDialog(self._current_context.get('decision_log', []), self).exec()
            )
            menu.addAction(audit_action)
            menu.addSeparator()

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
            real_action.triggered.connect(lambda: self._mark_word(word, 'real', widget, item, row))
            menu.addAction(real_action)

        if fake_enabled:
            fake_action = QAction('确认幻觉', self)
            fake_action.triggered.connect(lambda: self._mark_word(word, 'fake', widget, item, row))
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
            QMessageBox.information(self, '已存在', f'"{word}" 已在{("白名单" if action == "real" else "黑名单")}中。')
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
        self._settings_dialog = SettingsDialog(self, theme_callback=self.set_theme, current_theme=self.theme)
        self._settings_dialog.setWindowModality(Qt.WindowModality.NonModal)
        self._settings_dialog.show()


# ---- 入口 ----

def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName('GEHD')
    app.setApplicationVersion(GEHD_VERSION)
    app.setStyle('Fusion')

    theme_name = _load_theme_name()
    theme = Theme.find(theme_name) or Theme.default()
    window = MainWindow(theme)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
