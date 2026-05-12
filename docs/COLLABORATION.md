# GEHD 多智能体协作协议

> **参与方**: E / U / QA / D / PM / S  
> **仓库**: `https://github.com/Virukicy/GEHD`（Private）  
> **本地路径**: `~/Desktop/GEHD项目/`  
> **分支策略**: Trunk-Based（单 `main` 分支）  
> **最后更新**: 2026-05-12

---

## 一、团队结构

| 团队 | 简称 | 角色 | 源文件域 |
|------|------|------|------|
| E | E | 核心引擎开发、版本管理、CHANGELOG | `engine/` `io/` `cli/` `config/` `tests/`（引擎测试） `CHANGELOG.md` |
| U | U | 桌面 GUI 应用开发 | `gui/` `tests/test_gui.py` |
| QA | QA | 独立质量保障：代码审查、哨卡检查、合规扫描 | **无**（只读全部源文件，仅写 `.workbuddy/`） |
| D | D | 文档维护 | `docs/` `README.md` |
| PM | PM | 战略方向、场景审计、团队协调 | **无**（仅写 `.workbuddy/`） |
| S | S | 战略规划、架构设计、技术方向研究 | **无**（仅写 `workspace/S/` + `.workbuddy/`） |

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
├── PM/                   ← PM（决策记录、规划草稿）
└── S/                    ← S 组（路线图、架构方案、分析报告）
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

| 职责 | E | U | QA | D | PM | S |
|------|------|------|------|------|------|------|
| 引擎核心代码 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| GUI 界面代码 | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 版本号维护 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 配置文件 (config/*.json) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 测试（引擎） | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 测试（GUI） | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| 文档 (docs/) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| README.md | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| CHANGELOG.md | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| pyproject.toml | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| 代码审查 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 哨卡检查 | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| 路线图规划 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 架构方案 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 技术分析报告 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 场景审计 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| 团队协调 | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## 七、PM 指令与调度协议

### 7.1 PM 指令类型

PM 传递文档通过措辞区分指令类型。各组收到后须按对应流程执行。

**A 类：直接执行**

措辞特征：「执行」「完成」「修复」「更新」「迁移」「提交」。无前置条件。

流程：收到 → 执行 → 回执。

**B 类：先审后做**

措辞特征：「设计草案」「方案」「PM 确认后执行」「先出方案」「审批」。

流程：收到 → 产出草案/方案 → 回执附上 → 等待 PM 审批 → PM 批了再动工。

B 类指令的典型场景：新功能设计、架构变更、跨组影响的改动。

**C 类：信息通知**

措辞特征：「通知」「了解即可」「无需操作」「知会」。

流程：收到 → 阅读 → 无需回执。

### 7.2 PM 调度环

PM 通过以下循环分步推进跨组工作：

> PM 决策 → 助理出方案 → PM 审批 → 分步下发各组 → 各组回执 → 助理汇总 → PM 审阅 → 下一轮

操作原则：
- 有依赖关系的指令按顺序下发（如 E 建目录 → D 改协议 → 其他人迁移）
- 无依赖关系的指令并行下发（如 U 和 QA 同时迁移各自文件）
- 各组只写自己文件域，不同时操作同一文件则零冲突
- 全部回执后 PM 发 PM2A 宣布闭环

### 7.3 各组回执义务

| 指令类型 | 必须回执 | 回执内容 |
|------|:--:|------|
| A（直接执行） | 是 | 执行结果 + commit hash |
| B（先审后做） | 是 | 草案/方案，等审批后再执行 |
| C（信息通知） | 否 | — |

回执使用对应传递号前缀（E→PM 用 `E2PM`、U→PM 用 `U2PM`、QA→PM 用 `Q2PM`、D→PM 用 `D2PM`）。

### 7.4 决策文档化

PM 的重大决策（团队调整、流程变更、架构裁定）应在 `workspace/PM/decisions/` 下存档，文件名格式 `YYYY-MM-DD_简述.md`，方便后续追溯。

### 7.5 功能闭环循环

每项引擎功能完成（如 P2-3）后，在进入下一项功能（如 P2-4）之前，执行以下全组闭环：

| 顺序 | 谁 | 做什么 |
|:--:|:--:|------|
| 1 | QA | 对新增代码跑哨卡审查 |
| 2 | D | 同步架构文档、CHANGELOG |
| 3 | U | 自查新功能是否触发 GUI 变更需求 |
| 4 | PM | 汇总三方回执 → 决策下一阶段 |

第 1-3 步并行下发，各组只写自己文件域，无冲突。全部回执后 PM 批准 E 进入下一功能。

### 7.6 执行证据标准

当任何团队的回执声称"已运行工具/命令"时，回执内容必须包含可验证的执行产物。LLM 推理生成的内容不被视为执行证据。

**A. 原始输出强制附带**

凡回执中引用了命令执行结果（如 GEHD 扫描输出、pytest 结果、mypy 报告），必须逐字附带该命令的完整终端输出，不得删减、归纳或"分析后重述"。

**B. 产物引用**

命令执行生成的文件（如 `_l4_queue.json`、`coverage.json`）必须报告：
- 文件完整路径
- 关键数字（如实体数、测试数），不可仅描述"内容"
- 这些数字须与终端输出一致

**C. 段落号可追溯**

凡引用扫描结果（issues、warnings），每条须附带段落号，与终端原始输出中的段落号严格一致。

**D. PM 保留独立验证权**

PM 可自行运行相同命令交叉验证任何团队回执中的数字。若数字不一致，视为回执无效，发回重做。

### 7.7 S 组赋权说明

S（战略规划）组拥有**建议权**，PM 拥有**决策权和调度权**。

- S 可向 PM 提交路线图、架构方案、技术分析报告
- PM 决策后将形成 PM2X 指令，分发至各执行组
- S 不直接对 E/U/QA/D 发送指令或跨组协调
- S 与 PM 的通信使用 `S2PM` / `PM2S` 前缀，S 向全体广播使用 `S2A`

---

## 八、通讯协议

五方智能体不能直接对话。通讯方式：**用户在对话中转发**。

```
E  → 用户 → U / QA / D / PM / 全体
U  → 用户 → E / QA / D / PM / 全体
QA → 用户 → E / U / D / PM / 全体
D  → 用户 → E / U / QA / PM / 全体
PM → 用户 → E / U / QA / D / S / 全体
S  → 用户 → PM / 全体
```

> S 组通讯隔离：S 仅与 PM 直连，不直接对 E/U/QA/D 发指令。

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
| S→PM | `S2PM-YYYYMMDD-NNN` | `.workbuddy/` | `S2PM-20260512-001.md` |
| PM→S | `PM2S-YYYYMMDD-NNN` | `.workbuddy/` | `PM2S-20260512-001.md` |
| S→全体 | `S2A-YYYYMMDD-NNN` | `.workbuddy/` | `S2A-20260512-001.md` |

**规则**：
- 所有团队的传递统一写入项目 `.workbuddy/`
- 每次传递**新建文件**，不复用旧文件名
- 序号 NNN 按当天同方向递增
- 回复时在正文注明 `回复 {原传递号}`
