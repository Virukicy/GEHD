"""
文本提取器 —— 从 docx Document 对象中提取结构化文本块。

每个文本块包含：(位置标识, 文本内容)
  位置标识格式: "P1"（段落1）、"T2[3,1]"（表格2第3行第1列）
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from docx.document import Document


def extract_all_text(doc: Document) -> list[tuple[str, str]]:
    """从 docx 中提取所有有意义的文本片段及其位置信息。

    Args:
        doc: python-docx Document 对象

    Returns:
        [(位置标识, 文本), ...] 例如 [("P1", "第一章..."), ("T1[2,3]", "数据...")]
    """
    parts: list[tuple[str, str]] = []

    # 提取段落文本
    for i, para in enumerate(doc.paragraphs):
        if para.text.strip():
            parts.append((f"P{i + 1}", para.text))

    # 提取表格文本
    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                if cell.text.strip():
                    parts.append((f"T{ti + 1}[{ri + 1},{ci + 1}]", cell.text))

    return parts
