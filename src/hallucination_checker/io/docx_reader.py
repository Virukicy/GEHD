"""
文档读取器 —— 加载 .docx 文件，统一异常处理。

未来可扩展支持 .txt / .md / .pdf / .html 等格式。
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from docx import Document as _DocumentFactory

if TYPE_CHECKING:
    from docx.document import Document


def load_docx(filepath: str) -> Document:
    """加载 .docx 文件，含统一异常处理。

    Args:
        filepath: docx 文件路径

    Returns:
        python-docx Document 对象

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 文件损坏或无法解析
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f'文件不存在: {filepath}')

    try:
        doc = _DocumentFactory(filepath)
    except ValueError as e:
        raise ValueError(f'无法读取 docx 文件（格式损坏）: {e}') from e
    except OSError as e:
        raise ValueError(f'无法读取 docx 文件（IO错误）: {e}') from e

    return doc
