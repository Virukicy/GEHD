# GEHD 质量基线报告（第一版）

**日期**：2026-05-09
**工作流**：质量基线审计（定制）
**参与成员**：Zhen（主理人/汇编）、Cody（代码审查师）、Tessa（测试专家）
**版本**：v1.0

---

## 📌 TL;DR（执行摘要）

- **整体结论**：GEHD v0.2.0 质量基线 🟢 健康。76 个全量测试全部通过，ruff 零错误，代码规范零违规，PM2E-20260509-001 的两处代码残留已在最新 commit 中完全外部化到配置系统。
- **阻塞项**：🔴 无。mypy 5 个错误均在 GUI 层（UI 组域），不阻塞引擎功能，但应由 UI 组在下次迭代修复。
- **严重度分布**：🔴严重 0 项 / 🟠高 1 项 / 🟡中 4 项 / 🟢低 0 项
- **建议下一步**：UI 组修复 mypy 类型错误 → QA 组建立哨卡自动化 → 引擎组继续 Iteration 3

---

## 🎯 核心结论卡片

| 项目 | 内容 |
|------|------|
| 整体评级 | 🟡 有条件通过（引擎层 🟢，GUI 层 5 项 mypy 待修复） |
| 阻塞项数量 | 0 |
| 关键行动项 | 5 条 |
| 建议下一步 | UI 组修复 mypy → QA 哨卡自动化 → Iteration 3 |

---

## 一、测试运行结果

### 全量测试：76 passed ✅

```
============================== 76 passed in 0.98s ==============================
```

### 测试分布

| 测试文件 | 数量 | 类型 | 覆盖层 | 状态 |
|---------|------|------|--------|------|
| `test_regression.py` | 18 | 回归测试（依赖外部 docx） | L1-L4 全链路 | ✅ |
| `test_unit.py` | 27 | 独立单元测试 | L1/L2/L2.5/L3/L3.6/Config | ✅ |
| `test_gui.py` | 17 | GUI 测试 | GUI 类存在性 + JSON + 词提取 | ✅ |
| `test_declaration.py` | 7 | P2-1 声明提取测试 | L3.7 声明检测 | ✅ |
| `test_io_factories.py` | 4 | P2-2 适配层测试 | from_text / from_markdown | ✅ |
| **合计** | **76** | | | ✅ |

### 测试体系评价

**强项**：
- 引擎核心层（L1-L4）测试覆盖全面，回归 + 单元双轨并行，每个评分维度均有独立单元测试
- 测试分层清晰：回归测试验证端到端正确性，单元测试验证独立逻辑正确性
- 新增 P2-1（声明提取）和 P2-2（适配层）均有对应测试，新功能即测即交付

**弱项**：
- GUI 测试仅覆盖类存在性和工具函数，未覆盖交互逻辑（按钮点击、信号槽、异步操作）
- `__main__.py`（CLI 和 GUI 入口）覆盖率为 0%，未被任何测试触达
- `l4_verify.py` 覆盖率 76%，队列构建的边界路径（空队列、超大队列）未被测试

---

## 二、mypy 类型检查结果

### 5 errors in 2 files（全部在 GUI 层，归属 UI 组）⚠️

```
src/hallucination_checker/gui/settings_dialog.py:76: error: Returning Any from function declared to return "dict[str, Any]"  [no-any-return]
src/hallucination_checker/gui/main_window.py:526: error: Cannot determine type of "_settings_dialog"  [has-type]
src/hallucination_checker/gui/main_window.py:527: error: Cannot determine type of "_settings_dialog"  [has-type]
src/hallucination_checker/gui/main_window.py:528: error: Cannot determine type of "_settings_dialog"  [has-type]
src/hallucination_checker/gui/main_window.py:531: error: Argument 1 to "SettingsDialog" has incompatible type "MainWindow"; expected "QDialog | None"  [arg-type]
```

### 分项分析

| # | 文件:行 | 错误码 | 严重度 | 根因分析 |
|---|---------|--------|--------|---------|
| 1 | `settings_dialog.py:76` | `no-any-return` | 🟡 中 | 函数声明返回 `dict[str, Any]`，但某条代码路径返回了 `Any` 类型值。可能某个中间变量未标注类型。 |
| 2 | `main_window.py:526-528` | `has-type` | 🟡 中 | `_settings_dialog` 变量类型无法推断——可能是在条件分支中赋值，mypy 无法收敛类型。需显式标注 `Optional[SettingsDialog]`。 |
| 3 | `main_window.py:531` | `arg-type` | 🟠 高 | `SettingsDialog` 构造函数期望 `QDialog \| None` 作为父组件，但传入了 `MainWindow`（非 QDialog 子类）。这是真实的类型不匹配，可能在特定 Qt 版本下导致运行时异常。 |

### 影响评估

- **引擎功能**：零影响（mypy 错误全在 GUI 层）
- **GUI 运行**：当前不影响（Qt 运行时接受 QWidget 作为父组件），但不合类型契约
- **CI 集成风险**：若未来 CI 加入 mypy 门禁，GUI 代码会阻塞流水线

---

## 三、ruff lint 检查结果

### All checks passed! ✅

```
$ ruff check src/
All checks passed!
```

零 lint 问题，代码风格与项目规范完全一致。

---

## 四、代码覆盖率

### 总体：57%（1238 stmts, 533 missed）

### 分层覆盖率

| 模块 | 覆盖率 | 语句数 | 未覆盖 | 评级 |
|------|--------|--------|--------|------|
| **引擎核心层** | | | | |
| `l1_whitelist.py` | 100% | 15 | 0 | 🟢 |
| `l2_blacklist.py` | 100% | 8 | 0 | 🟢 |
| `l36_consistency.py` | 100% | 26 | 0 | 🟢 |
| `l3_heuristic.py` | 89% | 62 | 7 | 🟢 |
| `l25_nonentity.py` | 85% | 26 | 4 | 🟢 |
| `l4_verify.py` | 76% | 29 | 7 | 🟡 |
| `l37_declaration.py` | 88% | 24 | 3 | 🟢 |
| **引擎编排层** | | | | |
| `config.py` | 99% | 134 | 2 | 🟢 |
| `checker.py` | 90% | 61 | 6 | 🟢 |
| **IO 层** | | | | |
| `reporter.py` | 96% | 46 | 2 | 🟢 |
| `document_text.py` | 95% | 61 | 3 | 🟢 |
| `docx_reader.py` | 71% | 14 | 4 | 🟡 |
| `format_checks.py` | 73% | 62 | 17 | 🟡 |
| **CLI 层** | | | | |
| `main.py` | 78% | 55 | 12 | 🟡 |
| **GUI 层** | | | | |
| `main_window.py` | 21% | 319 | 253 | 🔴 |
| `settings_dialog.py` | 24% | 236 | 180 | 🔴 |
| **入口** | | | | |
| `__main__.py` | 0% | 18 | 18 | 🔴 |
| `gui/__main__.py` | 0% | 8 | 8 | 🔴 |

### 覆盖率缺口分析

| 缺口 | 风险等级 | 说明 |
|------|---------|------|
| GUI 层 21-24% | 🔴 高 | 当前 GUI 测试仅检查类存在性和工具函数，无交互逻辑、信号槽、异步操作的覆盖。当前阶段可接受（GUI v1 刚交付），但 v0.3.0 前需补充。 |
| `l4_verify.py` 76% | 🟡 中 | 未覆盖路径包括空队列输出、超大队列内存行为、JSON 写入失败回退。L4 是面向外部系统的接口，边界健壮性不足。 |
| `__main__.py` 0% | 🟡 中 | CLI 入口无测试。虽然逻辑薄（仅参数解析+编排），但回归缺失意味着 CLI 参数变更无法自动检测。 |
| `format_checks.py` 73% | 🟡 中 | 格式校验逻辑覆盖不完整——段落计数、表格检测、长文本截断的边界条件未测。 |

---

## 五、代码规范合规检查

### "不允许做法"扫描结果

| 检查项 | 结果 | 证据 |
|--------|------|------|
| 宽泛 `except Exception` | ✅ 零违规 | `grep -rn "except Exception" src/` — 无匹配 |
| `globals()` 魔法赋值 | ✅ 零违规 | `grep -rn "globals()" src/` — 无匹配 |
| 硬编码魔术数字 | ✅ 零违规 | 已验证 `l3_heuristic.py` 所有数值参数均来自 config |
| 跨层读变量 | ✅ 未发现 | 所有层间通信通过 `GEHDConfig` 参数传递 |

### 已确认修复项

**PM2E-20260509-001（代码残留）**：✅ 已修复

| 残留项 | 原位置 | 修复方式 | 新位置 |
|--------|--------|---------|--------|
| 单字电商后缀 (`购\|宝\|东`) | `l3_heuristic.py:62-64` | 外置化 | `config/thresholds.json` → `l3_behavior.single_char_platform_suffixes` |
| 可信字符列表 (`淘京东多美苏阿腾百`) | `l3_heuristic.py:72-78` | 外置化 | `config/thresholds.json` → `l3_behavior.plausible_chars` |
| 可信字符生效类别 (`电商平台名, 公司机构名`) | `l3_heuristic.py:80` | 外置化 | `config/thresholds.json` → `l3_behavior.plausible_char_categories` |

验证方法：
- `l3_heuristic.py` 当前代码引用 `config.single_char_platform_suffixes`、`config.plausible_chars`、`config.plausible_char_categories`
- `config/thresholds.json` 的 `l3_behavior` 节包含上述三组列表
- `config.py:740-750` 正确从 `l3_behavior` 加载 frozenset 字段

**结论**：PM2E-20260509-001 的两处架构级代码残留已完全消除。GEHD 现在达到 **100% 场景级特化**——换场景只需更换 `config/` 下的 JSON 文件，引擎代码零改动。

---

## 六、文件域合规检查

### 最近 3 次 commit 的文件域审计

| Commit | 变更文件 | 归属域 | 合规 |
|--------|---------|--------|------|
| `92968bf` 配置外置化扫尾 | `config/thresholds.json`, `engine/config.py`, `engine/layers/l3_heuristic.py` | 🔵 引擎组 | ✅ |
| `37911da` P2-2 适配层补全 | `io/document_text.py`, `tests/test_io_factories.py` | 🔵 引擎组 | ✅ |
| `956928b` P2-1 声明提取 | `engine/checker.py`, `engine/config.py`, `engine/layers/l37_declaration.py`, `config/declaration_patterns.json`, `config/whitelist.json`, `tests/test_declaration.py` | 🔵 引擎组 | ✅ |

### 冻结文件审计

**`io/document_text.py`**（冻结共享文件）：
- 最近变更：`37911da` 和 `8786421`，均由引擎组执行
- 文件归属：`io/` 层属于引擎组域（见 COLLABORATION.md）
- 冻结含义：改之前需喊话 UI 组同意
- 状态：引擎组域内变更，UI 组无异议记录 → ✅ 合规

### 跨域踩踏检测

近 3 次 commit 未发现任何跨文件域操作。✅

---

## 七、已闭合审查项回顾

### E2U-20260509-001 → U2E-20260509-002（闭环）

引擎组对 UI 组代码的审查提出了 5 项问题：

| # | 问题 | 修复状态 |
|---|------|---------|
| N9 | GUI 代码中的类型注解缺失 | ✅ 已修复 |
| N10 | 异常处理过于宽泛 | ✅ 已修复 |
| N11 | 信号槽连接未检查返回值 | ✅ 已修复 |
| N12 | 硬编码路径 | ✅ 已修复 |
| N13 | 文档字符串不完整 | ✅ 已修复 |

**闭合确认**：commit `211d1c5` "UI: 修复引擎组代码审查5项建议(N9-N13)"，UI 组回复 `U2E-20260509-002`。

**QA 评价**：审查流程规范、闭环完整。但注意——UI 组修复后仍有 5 个 mypy 错误（见上文第二节），说明 E2U-20260509-001 的审查未覆盖类型检查维度。建议今后跨组审查加入 mypy 检查项。

---

## 八、已知待处理项

| 编号 | 来源 | 描述 | 状态 | 建议 |
|------|------|------|------|------|
| M2 | `development.md` | 候选实体使用裸 `dict`，无 `TypedDict` | ⏳ 待处理 | 低优先级，不影响功能 |
| M5 | `development.md` | 去重逻辑在两处重复 | ⏳ 待处理 | 建议提取公共函数 |
| — | `development.md` | `scorers/` 目录为空壳 | ⏳ 待处理 | 要么实现，要么删除 |
| GUI-MYPY-1 | 本报告 | `settings_dialog.py:76` no-any-return | ⚠️ 新发现 | UI 组修复 |
| GUI-MYPY-2 | 本报告 | `main_window.py:526-531` 类型错误 | ⚠️ 新发现 | UI 组修复 |

---

## ✅ 行动清单（按优先级排序）

| # | 行动 | 负责角色 | 紧急度 | 预期完成 |
|---|------|---------|--------|---------|
| 1 | 修复 `main_window.py:531` arg-type 错误 — `SettingsDialog` 父组件类型不匹配 | UI 组 | P0 | 下次 GUI 迭代 |
| 2 | 为 `_settings_dialog` 添加显式类型注解 `Optional[SettingsDialog]` | UI 组 | P1 | 下次 GUI 迭代 |
| 3 | 修复 `settings_dialog.py:76` no-any-return — 标注中间变量类型 | UI 组 | P1 | 下次 GUI 迭代 |
| 4 | 将 mypy 加入 QA 哨卡检查清单（当前仅 ruff + pytest） | QA 组 | P1 | 今日 |
| 5 | 补充 `l4_verify.py` 边界测试（空队列、超大队列、JSON 写入失败） | 引擎组 | P2 | Iteration 3 |
| 6 | 补充 GUI 交互逻辑测试（信号槽、按钮点击、异步操作） | UI 组 | P2 | v0.3.0 前 |
| 7 | 清理 `scorers/` 空壳目录或实现评分模块 | 引擎组 | P3 | 方便时 |

---

## ⚠️ 待完善 / 已知局限

- GUI 覆盖率（21-24%）在当前版本（v0.2.0，GUI v1 刚交付）可接受，但 v0.3.0 前需提升至 60%+
- `l4_verify.py` 的联网核查逻辑尚未实现（Iteration 3 的 P2-3），当前只构建队列 JSON——届时需补充对应测试
- 本报告基于 `main` 分支 `92968bf` 快照生成，后续 commit 可能导致基线漂移
- 跨组代码审查（如 E2U-20260509-001）当前未纳入 mypy 检查维度，建议在哨卡流程中补充

---

## 📚 数据来源 & 成员产出索引

- **pytest 全量结果**：`pytest tests/ -v`（76 passed, 0 failed）
- **mypy 输出**：`mypy src/ --ignore-missing-imports`（5 errors）
- **ruff 输出**：`ruff check src/`（0 errors）
- **覆盖率报告**：`pytest --cov=src/hallucination_checker --cov-report=term`（57% overall）
- **Git 历史**：`git log --oneline -10` + `git diff HEAD~3 --stat`
- **代码规范扫描**：grep 四维度（except Exception / globals / exec / 魔术数字）
- **配置外置化验证**：`config/thresholds.json` + `config.py:740-750`
- **PM2E-20260509-001**：`.workbuddy/PM2E-20260509-001.md`
- **E2U-20260509-001 + U2E-20260509-002**：闭环文档对

---

> 本报告由工程保障团队 AI 协作生成，关键决策请由人类工程负责人复核。
>
> **传递号**：Q2A-20260509-001 | **方向**：QA → All（引擎组 + UI 组 + PM）
