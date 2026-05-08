"""
文档读取器 —— 加载 .docx 文件，统一异常处理。

未来可扩展支持 .txt / .md / .pdf / .html 等格式。
"""

import os

from docx import Document


def load_docx(filepath: str):
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
        doc = Document(filepath)
    except Exception as e:
        raise ValueError(f'无法读取 docx 文件: {e}') from e

    return doc
