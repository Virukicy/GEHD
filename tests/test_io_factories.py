"""DocumentText 工厂方法单元测试 — from_text + from_markdown。"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import tempfile
from pathlib import Path

from hallucination_checker.io.document_text import DocumentText


class TestFromText:
    """from_text 测试。"""

    def test_basic_text(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write('第一行\n第二行\n第三行')
            tmp = f.name

        try:
            doc = DocumentText.from_text(tmp)
            assert len(doc.parts) == 3
            assert doc.parts[0].text == '第一行'
            assert doc.parts[0].location == 'L1'
            assert doc.parts[0].display == 'L1'
            assert doc.parts[1].text == '第二行'
            assert doc.full_text == '第一行\n第二行\n第三行'
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write('')
            tmp = f.name

        try:
            doc = DocumentText.from_text(tmp)
            assert len(doc.parts) == 0
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_single_line(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write('唯一一行')
            tmp = f.name

        try:
            doc = DocumentText.from_text(tmp)
            assert len(doc.parts) == 1
            assert doc.parts[0].text == '唯一一行'
            assert doc.parts[0].location == 'L1'
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_lines_with_patterns(self):
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False, encoding='utf-8'
        ) as f:
            f.write('清华大学位于北京\n母丑购平台倒闭\nCEO宣布融资\n')
            tmp = f.name

        try:
            doc = DocumentText.from_text(tmp)
            assert len(doc.parts) == 3
            assert all(p.location.startswith('L') for p in doc.parts)
        finally:
            Path(tmp).unlink(missing_ok=True)


class TestFromMarkdown:
    """from_markdown 测试。"""

    def test_basic_markdown(self):
        content = '# 第一章\n\n这是正文内容。\n\n## 第二章\n\n更多正文。'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.md', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            doc = DocumentText.from_markdown(tmp)
            assert len(doc.parts) >= 2
            assert any(p.location.startswith('H1') for p in doc.parts)
            assert any('正文内容' in p.text for p in doc.parts)
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_heading_location(self):
        content = '# 标题测试\n\n段落文本。'
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.md', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            doc = DocumentText.from_markdown(tmp)
            headings = [p for p in doc.parts if p.location.startswith('H')]
            assert len(headings) >= 1
            assert headings[0].display == headings[0].location  # 非 P/T 格式，原样
        finally:
            Path(tmp).unlink(missing_ok=True)

    def test_empty_markdown(self):
        content = ''
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.md', delete=False, encoding='utf-8'
        ) as f:
            f.write(content)
            tmp = f.name

        try:
            doc = DocumentText.from_markdown(tmp)
            assert len(doc.parts) == 0
        finally:
            Path(tmp).unlink(missing_ok=True)
