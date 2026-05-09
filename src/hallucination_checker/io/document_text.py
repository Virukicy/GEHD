"""
文档中间表示 —— 引擎与各格式适配器之间的统一契约。

P2-2 设计（冻结）：
  - TextPart: 文本片段 + 位置标识 + 人类可读展示标签
  - DocumentText: 格式无关的文档表示，引擎唯一天然输入
  - 各 from_xxx() 工厂方法由 io 层适配器实现

冻结范围（v0.3.0 承诺）：
  - TextPart 字段名: location, text, display
  - DocumentText 字段名: parts, full_text
  - from_docx() 签名和返回值类型
  - gehd_check(text: DocumentText, ...) 签名（P2-2 实现）
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class TextPart:
    """文档中的单个文本片段。

    Attributes:
        location: 机器可读的位置标识（如 "P1", "T2[3,1]"）
        text: 文本内容
        display: 人类可读的位置标签（如 "段落 1", "表格 2 行 3 列 1"）
    """

    location: str
    text: str

    @property
    def display(self) -> str:
        """生成人类可读的位置标签。

        转换规则：
          P1       → 段落 1
          T2[3,1]  → 表格 2 行 3 列 1
          其他      → 原样返回
        """
        m = re.match(r'^P(\d+)$', self.location)
        if m:
            return f'段落 {m.group(1)}'

        m = re.match(r'^T(\d+)\[(\d+),(\d+)\]$', self.location)
        if m:
            return f'表格 {m.group(1)} 行 {m.group(2)} 列 {m.group(3)}'

        return self.location


@dataclass
class DocumentText:
    """格式无关的文档表示 —— 引擎的唯一天然输入。

    由各格式适配器负责构造：
      docx  → DocumentText.from_docx(path)
      txt   → DocumentText.from_text(path)
      md    → DocumentText.from_markdown(path)
      直接  → DocumentText(parts=[TextPart(...), ...])
    """

    parts: list[TextPart]
    full_text: str = field(init=False)

    def __post_init__(self):
        object.__setattr__(self, 'full_text', '\n'.join(p.text for p in self.parts))

    # ---- 工厂方法 ----

    @classmethod
    def from_docx(cls, filepath: str | Path) -> DocumentText:
        """从 .docx 文件构造 DocumentText。

        内部调用现有 docx_reader + text_extractor，零破坏性变更。
        """
        filepath = Path(filepath)

        # 延迟导入，避免循环依赖
        from hallucination_checker.engine.extractors.text_extractor import (
            extract_all_text,
        )
        from hallucination_checker.io.docx_reader import load_docx

        doc = load_docx(str(filepath))
        raw_parts = extract_all_text(doc)
        parts = [TextPart(location=loc, text=txt) for loc, txt in raw_parts]
        return cls(parts=parts)

    @classmethod
    def from_text(cls, filepath: str | Path) -> DocumentText:
        """从纯文本文件构造。

        P2-2 实现。每行一个 TextPart，location 格式为 "L{行号}"。
        """
        raise NotImplementedError('P2-2 适配后实现')

    @classmethod
    def from_markdown(cls, filepath: str | Path) -> DocumentText:
        """从 Markdown 文件构造。

        P2-2 实现。标题和段落各自一个 TextPart。
        """
        raise NotImplementedError('P2-2 适配后实现')
