"""GEHD 主题系统 — 设计令牌（Design Tokens）架构。

用法:
    theme = Theme(Path("themes/dark"))
    red_bg = theme.color("severity.issue.bg")  # → QColor('#4A2020')
"""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QColor


class Theme:
    """加载 theme.json + style.qss 的主题实例。"""

    def __init__(self, dir_path: Path) -> None:
        self._dir = dir_path
        theme_file = dir_path / 'theme.json'
        with open(theme_file, encoding='utf-8') as f:
            self._data: dict = json.load(f)

        qss_file = dir_path / 'style.qss'
        self._qss: str = qss_file.read_text(encoding='utf-8') if qss_file.exists() else ''

    def name(self) -> str:
        return str(self._data.get('name', self._dir.name))

    def dir_name(self) -> str:
        return self._dir.name

    def color(self, dot_path: str) -> QColor:
        """按点路径读取颜色。例: theme.color("severity.issue.bg")。"""
        tokens = self._data.get('tokens', {})
        value = tokens
        for key in dot_path.split('.'):
            if isinstance(value, dict):
                value = value.get(key, '#FF0000')
            else:
                return QColor('#FF0000')
        return QColor(str(value))

    def stylesheet(self) -> str:
        return self._qss

    @classmethod
    def discover(cls, base_dir: Path | None = None) -> list[Theme]:
        """扫描 themes/ 下所有子目录，返回 Theme 列表。"""
        if base_dir is None:
            base_dir = Path(__file__).resolve().parent / 'themes'
        themes: list[Theme] = []
        if not base_dir.is_dir():
            return themes
        for child in sorted(base_dir.iterdir()):
            if child.is_dir() and (child / 'theme.json').exists():
                themes.append(cls(child))
        return themes

    @classmethod
    def find(cls, dir_name: str, base_dir: Path | None = None) -> Theme | None:
        """按目录名查找已安装主题。"""
        for theme in cls.discover(base_dir):
            if theme.dir_name() == dir_name:
                return theme
        return None

    @classmethod
    def default(cls, base_dir: Path | None = None) -> Theme:
        """返回默认主题（default），不存在时返回第一个可用主题。"""
        th = cls.find('default', base_dir)
        if th:
            return th
        themes = cls.discover(base_dir)
        if themes:
            return themes[0]
        raise FileNotFoundError('未找到任何主题目录')
