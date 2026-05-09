# P2-2 适配层接口设计（已冻结）

> **版本**: frozen-1  
> **日期**: 2026-05-09  
> **状态**: U 已确认，E 已冻结  
> **对应代码**: `src/hallucination_checker/io/document_text.py`

---

## 一、核心决策

引擎不再直接接受 `docx.Document` 对象。所有输入统一为 `DocumentText`——格式无关的文档中间表示。

---

## 二、数据结构（冻结）

### TextPart

| 字段 | 类型 | 说明 |
|------|------|------|
| `location` | `str` | 机器可读位置标识（P1, T2[3,1]） |
| `text` | `str` | 文本内容 |
| `display` | `str` (property) | 人类可读位置标签（"段落 1", "表格 2 行 3 列 1"） |

`display` 自动从 `location` 生成，UI 层直接展示，无需理解格式差异。

### DocumentText

| 字段 | 类型 | 说明 |
|------|------|------|
| `parts` | `tuple[TextPart, ...]` | 有序文本片段（不可变） |
| `full_text` | `str` | `\n` 拼接的全文（自动缓存） |

### 工厂方法

| 方法 | 状态 | 说明 |
|------|------|------|
| `DocumentText.from_docx(path)` | ✅ 已实现 | 从 .docx 文件构造 |
| `DocumentText.from_text(path)` | ✅ 已实现 | 从纯文本文件构造 |
| `DocumentText.from_markdown(path)` | ✅ 已实现 | 从 Markdown 文件构造 |
| `DocumentText(parts=[...])` | ✅ | 直接从 TextPart 列表构造 |

---

## 三、新引擎入口（P2-2 实现）

```python
def gehd_check(
    text: DocumentText,
    config: GEHDConfig,
    output_verify_queue: bool = False,
) -> tuple[list[str], list[str], dict, list[dict]]:
```

返回值结构与 v0.2.0 完全相同，详见下文。

---

## 四、输出结构稳定承诺（v0.3.0）

**P2-3（联网核查）和 P2-4（证据链）不会改变以下结构：**

| 输出 | 类型 | 稳定度 |
|------|------|------|
| `issues` | `list[str]` | 🔒 不变 |
| `warnings` | `list[str]` | 🔒 不变 |
| `stats` 字典 | `dict` | 🔒 键名不变，P2-3 可追加新键 |
| `stats.total_candidates` | `int` | 🔒 不变 |
| `stats.l25_candidates` | `int` | 🔒 不变 |
| `stats.high_risk` | `int` | 🔒 不变 |
| `stats.medium_risk` | `int` | 🔒 不变 |
| `stats.low_risk` | `int` | 🔒 不变 |
| `stats.l4_queue_size` | `int` | 🔒 不变 |
| `l4_queue` | `list[dict]` | 🔒 元素结构不变 |

**P2-4（证据链）可能追加** `stats.evidence_count` 和 `l4_queue` 元素新增 `evidence` 字段——但现有字段不会删改。

---

## 五、适配层归属

**归属 `io/` 层。**

```
engine/  → 只处理 PlainText（DocumentText）
io/      → 各格式适配器（from_docx, from_text, from_markdown...）
```

---

## 六、向后兼容策略

| 版本 | `gehd_check(doc)` | `gehd_check(DocumentText)` |
|------|------|------|
| v0.2.0 | ✅ 当前 | — |
| **当前** | `gehd_check_docx()` (DeprecationWarning) | ✅ **主入口已切** |
| v0.3.0 | ❌ 移除 | ✅ 新接口 |

**当前状态**：新接口已实装。`gehd_check(DocumentText, ...)` 是主入口，CLI 已切换。
`gehd_check_docx()` 保留但触发 DeprecationWarning，v0.3.0 删除。

---

## 七、CLI 调用链（v0.3.0）

```
cli/main.py
  → DocumentText.from_docx(filepath)   # io 层适配
  → gehd_check(text, config)           # engine 层入口
  → reporter 输出
```

---

## 八、U 最小可用交付（已推送）

`DocumentText` + `from_docx()` 已推送到 main 分支。

U 现在可写：

```python
from hallucination_checker.io.document_text import DocumentText, TextPart
from hallucination_checker.engine.checker import gehd_check
from hallucination_checker.engine.config import load_config

config = load_config()
text = DocumentText.from_docx(filepath)
issues, warnings, stats, l4_queue = gehd_check(text, config)
# text.parts[0].display → "段落 1"（可直接展示）
# text.full_text         → 拼接全文
```

---

## 九、修订历史

| 日期 | 变更 |
|------|------|
| 2026-05-09 | 初版冻结（frozen-1） |
| 2026-05-09 | U 三点确认：display 字段、输出稳定、最小交付 |
| 2026-05-09 | gehd_check() 主入口切换到 DocumentText |
| 2026-05-09 | N8 修复：DocumentText 加 frozen=True，parts list→tuple |
