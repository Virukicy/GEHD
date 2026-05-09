# GEHD 多智能体协作协议

> **参与方**: 引擎组 AI（主智能体）、UI 组 AI（辅助智能体）  
> **仓库**: `https://github.com/Virukicy/GEHD`（Private）  
> **本地路径**: `~/Desktop/GEHD项目/`  
> **分支策略**: Trunk-Based（单 `main` 分支）  
> **最后更新**: 2026-05-09

---

## 一、核心原则：文件域分治

两个智能体共享一个 Git 仓库，各管各的文件域，互不踩脚。不建功能分支，两个智能体都直接往 `main` 推。

### 文件域划分

```
src/hallucination_checker/
├── engine/              ← 🔵 引擎组独占（layer/checker/config/extractors）
├── gui/                 ← 🟠 UI 组独占
├── io/
│   ├── document_text.py ← 🔒 冻结共享（改之前必须双方同意）
│   ├── docx_reader.py   ← 🔵 引擎组
│   ├── format_checks.py ← 🔵 引擎组
│   └── reporter.py      ← 🔵 引擎组
├── cli/                 ← 🔵 引擎组
├── __init__.py          ← 🔵 引擎组
├── __main__.py          ← 🔵 引擎组
└── logging_setup.py     ← 🔵 引擎组

config/                  ← 🔵 引擎组（UI 只读）
tests/
├── test_regression.py   ← 🔵 引擎组
├── test_unit.py         ← 🔵 引擎组
├── test_gui.py          ← 🟠 UI 组（新建）
└── conftest.py          ← 🔵 引擎组（改之前喊话）
docs/                    ← 🔵 引擎组维护
pyproject.toml           ← 🔵 引擎组（版本号等）
README.md / CHANGELOG.md ← 🔵 引擎组
```

### 三条铁律

1. **开工前 `git pull`** — 确保拿到对方最新代码
2. **只改自己域内文件** — 碰共享/冻结文件前先在对话里喊话
3. **改完立即 `git push`** — 不让对方等

---

## 二、标准工作流

### 引擎组开工

```bash
git pull
# 改代码（只动 engine/ io/ cli/ config/ 等引擎域文件）
git add -A
git commit -m "Engine: 做了什么"
git pull --rebase
git push
```

### UI 组开工

```bash
git pull
# 改代码（只动 gui/ 和 tests/test_gui.py）
git add -A
git commit -m "UI: 做了什么"
git pull --rebase
git push
```

### `--rebase` 说明

如果你的 commit 在对方之后才推，`rebase` 会把你的改动"接在"对方后面，避免分叉的 merge commit，保持历史一条直线。

```
对方: A → B → C
你:   A → B → D        ← 先 rebase，变成 A → B → C → D，再 push
```

---

## 三、冲突处理

| 场景 | 怎么做 |
|------|------|
| 同时改**不同文件** | `git pull --rebase` 自动合并，零冲突 |
| 同时改**同一文件** | 文件域分治下不应发生。如发生，后 push 的人 `git pull --rebase` 后手动解决冲突 |
| 需改**冻结共享文件** | 对话里喊话对方，同意后再改 |
| 需改**对方域文件** | 对话里提需求，让对方改 |

---

## 四、共享冻结接口

UI 组可直接调用的引擎接口（签名已冻结，详见 `docs/p2-2-interface.md`）：

```python
from hallucination_checker.io.document_text import DocumentText, TextPart
from hallucination_checker.engine.checker import gehd_check
from hallucination_checker.engine.config import GEHDConfig, load_config

config = load_config()
text = DocumentText.from_docx(filepath)
issues, warnings, stats, l4_queue = gehd_check(text, config)
```

这些类和函数的公开签名在 v0.3.0 内不会变化。要改签名先喊话引擎组。

---

## 五、双方全责清单

| 职责 | 引擎组 | UI 组 |
|------|------|------|
| 引擎核心代码 | ✅ | ❌ |
| GUI 界面代码 | ❌ | ✅ |
| 版本号维护 | ✅ | ❌ |
| 配置文件 (config/*.json) | ✅ | ❌ |
| 测试（引擎） | ✅ | ❌ |
| 测试（GUI） | ❌ | ✅ |
| 文档 (docs/) | ✅ | ❌ |
| CHANGELOG | ✅ | ❌ |
| pyproject.toml | ✅ | ❌ |

---

## 六、通讯协议

两个智能体不能直接对话。通讯方式：**用户在对话中转发**。

```
UI 组 → 用户（转发）→ 引擎组
引擎组 → 用户（转发）→ UI 组
```

需要协作时在对话里 @ 对方，用户来做"人肉消息总线"。

### 传递文档规范

正式传递写入 `~/.workbuddy/` 目录，使用以下命名和编号：

| 方向 | 文件名 | 传递号格式 |
|------|------|------|
| 引擎→UI | `ENGINE_TO_UI.md` | `E2U-YYYYMMDD-NNN` |
| UI→引擎 | `UI_TO_ENGINE.md` | `U2E-YYYYMMDD-NNN` |

每次写入前先读取已有传递文档，确认传递号不重复。回复对方时引用原传递号。

**示例**：
- 引擎组首次发送 → 写入 `ENGINE_TO_UI.md`，传递号 `E2U-20260509-001`
- UI 组收到后回复 → 写入 `UI_TO_ENGINE.md`，传递号 `U2E-20260509-001`，正文注明「回复 E2U-20260509-001」
