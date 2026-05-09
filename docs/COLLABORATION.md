# GEHD 多智能体协作协议

> **参与方**: E / U / QA / D / PM  
> **仓库**: `https://github.com/Virukicy/GEHD`（Private）  
> **本地路径**: `~/Desktop/GEHD项目/`  
> **分支策略**: Trunk-Based（单 `main` 分支）  
> **最后更新**: 2026-05-09

---

## 一、团队结构

| 团队 | 简称 | 角色 | 源文件域 |
|------|------|------|------|
| E | E | 核心引擎开发、版本管理、CHANGELOG | `engine/` `io/` `cli/` `config/` `tests/`（引擎测试） `CHANGELOG.md` |
| U | U | 桌面 GUI 应用开发 | `gui/` `tests/test_gui.py` |
| QA | QA | 独立质量保障：代码审查、哨卡检查、合规扫描 | **无**（只读全部源文件，仅写 `.workbuddy/`） |
| D | D | 文档维护 | `docs/` `README.md` |
| PM | PM | 战略方向、场景审计、团队协调 | **无**（仅写 `.workbuddy/`） |

---

## 二、文件域划分

```
src/hallucination_checker/
├── engine/              ← 🔵 E 独占
├── gui/                 ← 🟠 U 独占
├── io/
│   ├── document_text.py ← 🔒 冻结共享（改之前必须 E+U 双方同意）
│   ├── docx_reader.py   ← 🔵 E
│   ├── format_checks.py ← 🔵 E
│   └── reporter.py      ← 🔵 E
├── cli/                 ← 🔵 E
├── __init__.py          ← 🔵 E
├── __main__.py          ← 🔵 E
└── logging_setup.py     ← 🔵 E

config/                  ← 🔵 E（U 只读）
tests/
├── test_regression.py   ← 🔵 E
├── test_unit.py         ← 🔵 E
├── test_declaration.py  ← 🔵 E
├── test_io_factories.py ← 🔵 E
├── test_gui.py          ← 🟠 U
└── conftest.py          ← 🔵 E（改之前喊话）

docs/                    ← 📗 D 独占
README.md                ← 📗 D 独占
CHANGELOG.md             ← 🔵 E 自行维护
pyproject.toml           ← 🔵 E（版本号等）

🟢 QA: 只读全部源文件，仅写 .workbuddy/ 传递文档
🟢 PM: 仅写 .workbuddy/ 传递文档
📗 D:  docs/ + README.md，仅改文档
```

### workspace/ 分区

```
workspace/                ← 各组过程文件分区（gitignored）
├── E/                    ← E 组（设计文档、技术方案）
├── U/                    ← U 组（截图、迭代计划）
├── QA/                   ← QA 组（基线数据、审计报告、覆盖率）
├── D/                    ← D 组（文档草稿、审计清单）
└── PM/                   ← PM（决策记录、规划草稿）
```

规则：
- `workspace/` 在 `.gitignore` 中，不推 GitHub
- 各组只读写自己的 `workspace/{E,U,QA,D,PM}/`
- 组内可自由创建子目录，以组内 README.md 为约定
- 过程文件在此分区内存活，不受版本发布影响

---

## 三、条条铁律

1. **开工前 `git pull`** — 确保拿到最新代码
2. **只改自己域内文件** — 碰共享/冻结文件前先喊话
3. **改完立即 `git push`** — 不让其他组等
4. **QA 有哨卡通过权** — 未通过哨卡的 commit，对应团队需修复

---

## 四、标准工作流

### E / U 开工

```bash
git pull
# 改代码（只动自己域内的文件）
git add -A
git commit -m "Team: 做了什么"
git pull --rebase
git push
```

### 提交后 QA 哨卡

QA 每次提交后自动执行：

```
pytest                    ← 全量测试是否通过？
mypy src/                ← 有无新增类型错误？
ruff check src/          ← 有无新增 lint 问题？
git diff --stat          ← 是否踩到其他组的文件域？
```

**通过** → QA 产出简短确认。**不通过** → QA 产出 `Q2E-YYYYMMDD-NNN`（E）或 `Q2U-YYYYMMDD-NNN`（U），列明问题。

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

| 职责 | E | U | QA | D | PM |
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

五方智能体不能直接对话。通讯方式：**用户在对话中转发**。

```
E  → 用户 → U / QA / D / PM / 全体
U  → 用户 → E / QA / D / PM / 全体
QA → 用户 → E / U / D / PM / 全体
D  → 用户 → E / U / QA / PM / 全体
PM → 用户 → E / U / QA / D / 全体
```

### 传递文档规范

正式传递写入 `.workbuddy/` 目录，**文件名即传递号**。

| 方向 | 前缀 | 位置 | 示例 |
|------|------|------|------|
| E→U | `E2U-YYYYMMDD-NNN` | `.workbuddy/` | `E2U-20260509-001.md` |
| E→QA | `E2Q-YYYYMMDD-NNN` | `.workbuddy/` | `E2Q-20260509-001.md` |
| E→D | `E2D-YYYYMMDD-NNN` | `.workbuddy/` | `E2D-20260509-001.md` |
| E→PM | `E2PM-YYYYMMDD-NNN` | `.workbuddy/` | `E2PM-20260509-001.md` |
| E→全体 | `E2A-YYYYMMDD-NNN` | `.workbuddy/` | `E2A-20260509-001.md` |
| U→E | `U2E-YYYYMMDD-NNN` | `.workbuddy/` | `U2E-20260509-001.md` |
| U→QA | `U2Q-YYYYMMDD-NNN` | `.workbuddy/` | `U2Q-20260509-001.md` |
| U→D | `U2D-YYYYMMDD-NNN` | `.workbuddy/` | `U2D-20260509-001.md` |
| U→PM | `U2PM-YYYYMMDD-NNN` | `.workbuddy/` | `U2PM-20260509-001.md` |
| U→全体 | `U2A-YYYYMMDD-NNN` | `.workbuddy/` | `U2A-20260509-001.md` |
| QA→E | `Q2E-YYYYMMDD-NNN` | `.workbuddy/` | `Q2E-20260509-001.md` |
| QA→U | `Q2U-YYYYMMDD-NNN` | `.workbuddy/` | `Q2U-20260509-001.md` |
| QA→D | `Q2D-YYYYMMDD-NNN` | `.workbuddy/` | `Q2D-20260509-001.md` |
| QA→PM | `Q2PM-YYYYMMDD-NNN` | `.workbuddy/` | `Q2PM-20260509-001.md` |
| QA→全体 | `Q2A-YYYYMMDD-NNN` | `.workbuddy/` | `Q2A-20260509-001.md` |
| D→E | `D2E-YYYYMMDD-NNN` | `.workbuddy/` | `D2E-20260509-001.md` |
| D→U | `D2U-YYYYMMDD-NNN` | `.workbuddy/` | `D2U-20260509-001.md` |
| D→QA | `D2Q-YYYYMMDD-NNN` | `.workbuddy/` | `D2Q-20260509-001.md` |
| D→PM | `D2PM-YYYYMMDD-NNN` | `.workbuddy/` | `D2PM-20260509-001.md` |
| D→全体 | `D2A-YYYYMMDD-NNN` | `.workbuddy/` | `D2A-20260509-001.md` |
| PM→E | `PM2E-YYYYMMDD-NNN` | `.workbuddy/` | `PM2E-20260509-001.md` |
| PM→U | `PM2U-YYYYMMDD-NNN` | `.workbuddy/` | `PM2U-20260509-001.md` |
| PM→QA | `PM2Q-YYYYMMDD-NNN` | `.workbuddy/` | `PM2Q-20260509-001.md` |
| PM→D | `PM2D-YYYYMMDD-NNN` | `.workbuddy/` | `PM2D-20260509-001.md` |
| PM→全体 | `PM2A-YYYYMMDD-NNN` | `.workbuddy/` | `PM2A-20260509-001.md` |

**规则**：
- 所有团队的传递统一写入项目 `.workbuddy/`
- 每次传递**新建文件**，不复用旧文件名
- 序号 NNN 按当天同方向递增
- 回复时在正文注明 `回复 {原传递号}`
