# GEHD 多智能体协作协议

> **参与方**: 引擎组 / UI 组 / QA 组 / 文档组 / PM  
> **仓库**: `https://github.com/Virukicy/GEHD`（Private）  
> **本地路径**: `~/Desktop/GEHD项目/`  
> **分支策略**: Trunk-Based（单 `main` 分支）  
> **最后更新**: 2026-05-09

---

## 一、团队结构

| 团队 | 简称 | 角色 | 源文件域 |
|------|------|------|------|
| 引擎组 | ENG | 核心引擎开发、版本管理、CHANGELOG | `engine/` `io/` `cli/` `config/` `tests/`（引擎测试） `CHANGELOG.md` |
| UI 组 | UI | 桌面 GUI 应用开发 | `gui/` `tests/test_gui.py` |
| QA 组 | QA | 独立质量保障：代码审查、哨卡检查、合规扫描 | **无**（只读全部源文件，仅写 `.workbuddy/`） |
| 文档组 | DOC | 文档维护 | `docs/` `README.md` |
| PM | PM | 战略方向、场景审计、团队协调 | **无**（仅写 `.workbuddy/`） |

---

## 二、文件域划分

```
src/hallucination_checker/
├── engine/              ← 🔵 引擎组独占
├── gui/                 ← 🟠 UI 组独占
├── io/
│   ├── document_text.py ← 🔒 冻结共享（改之前必须引擎+UI双方同意）
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
├── test_declaration.py  ← 🔵 引擎组
├── test_io_factories.py ← 🔵 引擎组
├── test_gui.py          ← 🟠 UI 组
└── conftest.py          ← 🔵 引擎组（改之前喊话）

docs/                    ← 📗 文档组独占
README.md                ← 📗 文档组独占
CHANGELOG.md             ← 🔵 引擎组自行维护
pyproject.toml           ← 🔵 引擎组（版本号等）

🟢 QA 组: 只读全部源文件，仅写 .workbuddy/ 传递文档
🟢 PM:   仅写 .workbuddy/ 传递文档
📗 DOC:  docs/ + README + CHANGELOG，仅改文档
```

---

## 三、条条铁律

1. **开工前 `git pull`** — 确保拿到最新代码
2. **只改自己域内文件** — 碰共享/冻结文件前先喊话
3. **改完立即 `git push`** — 不让其他组等
4. **QA 有哨卡通过权** — 未通过哨卡的 commit，对应团队需修复

---

## 四、标准工作流

### 引擎组 / UI 组开工

```bash
git pull
# 改代码（只动自己域内的文件）
git add -A
git commit -m "Team: 做了什么"
git pull --rebase
git push
```

### 提交后 QA 哨卡

QA 组每次提交后自动执行：

```
pytest                    ← 全量测试是否通过？
mypy src/                ← 有无新增类型错误？
ruff check src/          ← 有无新增 lint 问题？
git diff --stat          ← 是否踩到其他组的文件域？
```

**通过** → QA 产出简短确认。**不通过** → QA 产出 `Q2E-YYYYMMDD-NNN`（引擎）或 `Q2U-YYYYMMDD-NNN`（UI），列明问题。

### `--rebase` 说明

如果你的 commit 在对方之后才推，`rebase` 会把你的改动接在对方后面，避免分叉的 merge commit。

```
对方: A → B → C
你:   A → B → D        ← 先 rebase，变成 A → B → C → D，再 push
```

---

## 五、冲突处理

| 场景 | 怎么做 |
|------|------|
| 同时改**不同文件** | `git pull --rebase` 自动合并 |
| 同时改**同一文件** | 文件域分治下不应发生。如发生，后 push 的人手动解决 |
| 需改**冻结共享文件** | 对话喊话相关方，同意后再改 |
| 需改**对方域文件** | 对话提需求，让对方改 |
| QA 审查不通过 | 修复或通过传递文档回复，不让审查项悬空 |

---

## 六、全责清单

| 职责 | 引擎组 | UI 组 | QA 组 | 文档组 | PM |
|------|------|------|------|------|------|
| 引擎核心代码 | ✅ | ❌ | ❌ | ❌ | ❌ |
| GUI 界面代码 | ❌ | ✅ | ❌ | ❌ | ❌ |
| 版本号维护 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 配置文件 (config/*.json) | ✅ | ❌ | ❌ | ❌ | ❌ |
| 测试（引擎） | ✅ | ❌ | ❌ | ❌ | ❌ |
| 测试（GUI） | ❌ | ✅ | ❌ | ❌ | ❌ |
| 文档 (docs/) | ❌ | ❌ | ❌ | ✅ | ❌ |
| README.md | ❌ | ❌ | ❌ | ✅ | ❌ |
| CHANGELOG.md | ✅ | ❌ | ❌ | ❌ | ❌ |
| pyproject.toml | ✅ | ❌ | ❌ | ❌ | ❌ |
| 代码审查 | ❌ | ❌ | ✅ | ❌ | ❌ |
| 哨卡检查 | ❌ | ❌ | ✅ | ❌ | ❌ |
| 场景审计 | ❌ | ❌ | ❌ | ❌ | ✅ |
| 团队协调 | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 七、通讯协议

四方智能体不能直接对话。通讯方式：**用户在对话中转发**。

```
引擎组 → 用户 → UI 组 / QA 组 / PM
UI 组  → 用户 → 引擎组 / QA 组 / PM
QA 组  → 用户 → 引擎组 / UI 组
PM     → 用户 → 引擎组 / UI 组 / QA 组
```

### 传递文档规范

正式传递写入 `.workbuddy/` 目录，**文件名即传递号**。

| 方向 | 前缀 | 位置 | 示例 |
|------|------|------|------|
| 引擎→UI | `E2U-YYYYMMDD-NNN` | `~/.workbuddy/` | `E2U-20260509-001.md` |
| UI→引擎 | `U2E-YYYYMMDD-NNN` | `.workbuddy/` | `U2E-20260509-001.md` |
| QA→引擎 | `Q2E-YYYYMMDD-NNN` | `.workbuddy/` | `Q2E-20260509-001.md` |
| QA→UI | `Q2U-YYYYMMDD-NNN` | `.workbuddy/` | `Q2U-20260509-001.md` |
| QA→全体 | `Q2A-YYYYMMDD-NNN` | `.workbuddy/` | `Q2A-20260509-001.md` |
| 文档组→引擎 | `D2E-YYYYMMDD-NNN` | `.workbuddy/` | `D2E-20260509-001.md` |
| 文档组→UI | `D2U-YYYYMMDD-NNN` | `.workbuddy/` | `D2U-20260509-001.md` |
| 文档组→QA | `D2Q-YYYYMMDD-NNN` | `.workbuddy/` | `D2Q-20260509-001.md` |
| 文档组→全体 | `D2A-YYYYMMDD-NNN` | `.workbuddy/` | `D2A-20260509-001.md` |
| PM→引擎 | `PM2E-YYYYMMDD-NNN` | `.workbuddy/` | `PM2E-20260509-001.md` |
| PM→UI | `PM2U-YYYYMMDD-NNN` | `.workbuddy/` | `PM2U-20260509-001.md` |
| PM→QA | `PM2Q-YYYYMMDD-NNN` | `.workbuddy/` | `PM2Q-20260509-001.md` |
| PM→文档组 | `PM2D-YYYYMMDD-NNN` | `.workbuddy/` | `PM2D-20260509-001.md` |

**规则**：
- 引擎组的传出传递写入 `~/.workbuddy/`，其他所有团队的传递写入项目的 `.workbuddy/`
- 每次传递**新建文件**，不复用旧文件名
- 序号 NNN 按当天同方向递增
- 回复时在正文注明 `回复 {原传递号}`
