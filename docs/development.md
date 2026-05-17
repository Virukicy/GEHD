# GEHD 开发指南

> **版本**：v0.5.2  
> **最后更新**：2026-05-17  
> **前置阅读**：先读 [architecture.md](./architecture.md) 了解项目结构

---

## 一、环境搭建

### 前置要求

- Python ≥ 3.11
- Git

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/Virukicy/GEHD.git
cd GEHD

# 2. 安装依赖
pip install -e .

# 3. 运行
python -m hallucination_checker path/to/document.docx --mode full
```

### 开发依赖

```bash
pip install -e ".[dev]"   # 含 pytest、mypy、ruff
```

`pyproject.toml` 中定义了完整的依赖声明。

---

## 二、项目结构速查

### 核心引擎入口

```python
from hallucination_checker.engine.pipeline import run_pipeline, PipelineContext

# 创建管道上下文
ctx = PipelineContext(text=text, config=config)

# 三路径调用
result = run_pipeline(ctx, mode='full')     # 规则+搜索+LLM 全链路
result = run_pipeline(ctx, mode='fast')     # 规则+LLM 直接核验，零搜索开销
result = run_pipeline(ctx, mode='offline')  # 纯规则，零 API 成本
```

PipelineContext 关键字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `candidates` | list[dict] | 规则引擎输出的候选实体（含评分） |
| `l4_queue` | list[dict] | L4 待联网验证队列 |
| `decision_log` | list[dict] | 每个管道阶段的决策追溯记录 |
| `status` | PipelineStatus | 当前管道运行状态 |
| `stage_results` | dict | 各阶段输出数据，键为阶段名 |

### 各层独立调用

```python
# L1 白名单
from hallucination_checker.engine.layers.l1_whitelist import check_substring_whitelist
matched, skip, remainder = check_substring_whitelist("华为技术有限公司")

# L3 启发式评分
from hallucination_checker.engine.layers.l3_heuristic import extract_and_score, deduplicate_entities
candidates = extract_and_score(all_parts, full_text)
ranked = deduplicate_entities(candidates)
```

### 配置修改

所有配置在 `config/*.json` 中。修改后下次运行自动生效，无需改 Python 代码。

```bash
# 加一个白名单词
echo '"新公司名"' >> config/whitelist.json   # 或直接编辑 JSON 数组

# 调整高危阈值
# 编辑 config/thresholds.json → scores.high_threshold
```

---

## 三、运行与测试

### CLI 使用

```bash
# 完整模式（规则+搜索+LLM 全链路）
python -m hallucination_checker document.docx --mode full

# 快速模式（规则+LLM 直接核验，零搜索）
python -m hallucination_checker document.docx --mode fast

# 离线模式（纯规则，零 API 成本）
python -m hallucination_checker document.docx --mode offline

# 审计模式（输出完整 decision_log JSON）
python -m hallucination_checker document.docx --audit
```

### 运行测试

```bash
# 全量测试
pytest tests/ -v

# 预期：127 passed
```

**注意**：测试依赖 `GEHD_RedTeam_v2_Document.docx`，路径见 `tests/conftest.py`。

### 测试覆盖范围（v0.4.0-alpha）

测试套件已扩展至 76 个测试，覆盖所有层和 IO 入口：

| 测试文件/目录 | 覆盖层 |
|------|------|
| `tests/test_regression.py` | L1-L4 回归测试 |
| `tests/test_unit.py` | L1-L4 各层单元测试 |
| `tests/test_declaration.py` | L3.7 声明提取 |
| `tests/test_io_factories.py` | IO 工厂方法 |
| `tests/test_gui.py` | GUI 组件 |
| `tests/test_layers/` | 分层独立测试 |
| `tests/test_io/` | IO 层独立测试 |

---

## 四、代码规范

### 模块命名

```
engine/layers/l1_whitelist.py   — L1 层：白名单放行
engine/layers/l2_blacklist.py   — L2 层：黑名单拦截
engine/layers/l25_nonentity.py  — L2.5 层：非实体幻觉
engine/layers/l3_heuristic.py   — L3 层：启发式评分
engine/layers/l36_consistency.py — L3.6 层：一致性检查
engine/layers/l37_declaration.py — L3.7 层：声明提取
engine/layers/l4_verify.py      — L4 层：验证队列
```

### 类型注解（已完成，v0.2.0）

- 引擎层（`engine/layers/`）：**有**完整类型注解
- IO 层（`io/`）：**有**完整类型注解（P1-1 已修复）
- CLI 层：**有**完整类型注解
- mypy 22 文件零错误

### 不允许的做法

- ❌ `except Exception` 宽泛捕获（除非有 `raise` 重新抛出）
- ❌ `globals()` 或 `exec()` 魔法赋值（v0.1.1 已重构）
- ❌ 硬编码魔术数字（v0.1.2 已提取 `DEEP_SEARCH_THRESHOLD`）
- ❌ 跨层直接读取其他层的内部变量（必须通过函数接口）

---

## 五、关键设计决策

### 为什么是管道架构而非单体引擎？

v0.3.0 的 GEHD 是纯规则引擎——所有逻辑在一个 `gehd_check()` 函数中顺序执行。v0.4.0 引入 LLM 后，管道增加了前置过滤和后置纠正两个步骤。但这些步骤通过 if/else 硬编码接线，导致 v0.4.0-rc 端到端验收触发 8 次修复——接线缺失（4 次）、数据缺失（2 次）、字段不对齐（1 次）、配置读后丢弃（1 次）。

v0.5.0 的管道架构用双层契约（STAGE_CONTRACTS + ADAPTER_CONTRACTS）在启动时一次性验证所有前置条件，从架构层面消灭了这些故障类别。

### 为什么三路径而非一刀切？

| 模式 | 适用场景 | API 消耗 | 可信度 |
|------|------|:--:|:--:|
| full | 关键文档（合同/财报/研报） | Tavily + LLM | 最高 |
| fast | 批量初步扫描 | 仅 LLM | 中 |
| offline | 无网络环境 / 零成本 | 0 | 基础 |

用户根据场景选择，而不是引擎替用户决定。

### 为什么配置用 JSON 而非 YAML/TOML？

JSON 是 Python 标准库原生支持（无需额外依赖），且对非程序员友好（直接编辑数组）。

### 为什么 `L2.5` 在 `L3` 之前？

L2.5 检测的是"非实体幻觉"——统计数据、引述、时间线。这些比 L3 的专有名词检测更危险（编造的数字可能被当成事实），所以优先级更高。

### 为什么频率信号加分？

AI 幻觉的一个特征：虚构的核心概念会在文档中被反复提及（公司名、产品名频繁出现）。真正的冷门实体通常只出现一两次。

### GUI + CLI + AI 三者如何共存？（P1-0 设计原则）

GEHD 的三类消费者——用户（GUI）、命令行（CLI）、AI 代理——共享同一份配置和同一个引擎：

```
用户 → GUI ──┐
             ├──→ GEHD 引擎 ──→ config/*.json（唯一真实来源）
AI  → CLI ──┘
```

**铁律**：
- 配置的唯一真实来源是 `config/*.json` 文件
- GUI 不得将配置藏进自己的数据库或私有状态
- AI 代理通过编辑 JSON 文件实现自迭代（加白名单、更新黑名单等）
- 引擎启动时从 JSON 加载，任何修改在下次运行时自动生效

### AI 自迭代循环说明

AI 代理使用 GEHD 的完整流程（详见 [ai-guide.md](./ai-guide.md)）：

1. AI 调用 GEHD 扫描文档 → 获得 issues/warnings/L4 队列
2. AI 对 L4 队列中的候选词进行联网验证
3. AI 将验证结果写入 `_l4_cache.json`
4. AI 根据验证结果更新 `config/*.json`（如同一个词频繁被误报则加入白名单）
5. 下次扫描时，引擎自动加载更新后的配置

---

## 六、常见修改场景

### 场景 A：加一个白名单词

1. 编辑 `config/whitelist.json`，在 `whitelist` 数组中加一行
2. 重新运行核查，新词会被自动放行

### 场景 B：调整评分敏感度

1. 编辑 `config/thresholds.json`
2. `high_threshold`：提高 → 更少高危标记；降低 → 更敏感
3. `medium_threshold`：提高 → 更少中危标记

### 场景 C：添加新的实体类型检测

1. 在 `config/entity_patterns.json` 的 `patterns` 数组中添加一条：
   ```json
   {"pattern": "你的正则", "category": "新类别", "base_score": 45}
   ```
2. 如需特殊评分逻辑，在 `engine/layers/l3_heuristic.py` 的 `extract_and_score()` 中添加

### 场景 D：修复一个误报

1. 如果某个正常词汇被误判为幻觉，将其加入 `config/exclude_words.json`
2. 如果某类模式整体误报率高，调整 `config/entity_patterns.json` 中的 `base_score`

---

## 七、当前已知技术债务

> 最后验证：v0.4.0-alpha（2026-05-13）。

| 编号 | 问题 | 状态 |
|------|------|------|
| M2 | 候选实体使用裸 `dict`，无 `TypedDict` | ⏳ 待处理 |
| M5 | 去重逻辑在三处独立实现（L3/L2.5/L3.7），可提取公共函数 | ⏳ 待处理 |
| — | `scorers/` 目录为空壳 | ⏳ 待处理 |

### 设计决策：print vs logging

终端用户输出保持 `print()`，内部诊断使用 `logging` 写 `gehd.log`。
原因：`StreamHandler` 绑定对象引用而非变量名，测试框架替换 `sys.stdout` 时无法跟随。
功能零损失——日志含时间戳和结构化消息，满足审计需求。

---

## 九、过程哲学 — 模型分工与增量交付

GEHD 团队使用分层模型策略，以模型能力差异强制执行工程纪律。

### 模型分工

| 组 | 模型 | 原因 |
|:--:|:--:|------|
| PM / E / U / QA / D | DeepSeek Flash | 低成本，天然限制一次交付规模 |
| S | DeepSeek Pro | 架构推理需全量上下文 |

### 增量交付纪律

Flash 模型的能力天花板 = 天然强制执行增量交付。v0.5.0 架构革新过于激进（E 和 U 同时改动、接口未冻结、三模式同时暴雷），正是因为 Pro 模型能"一次写五个文件"的便利性消解了谨慎。

当前纪律：
- E 一次交付不超过 3 个源文件
- 重大架构变更必须先冻结接口（见 COLLABORATION.md §7.8）
- 任何跨 E/U 的功能，E 先完成接口定义并冻结，U 再基于冻结接口并行开发

这不是省钱策略，是工程纪律策略。

---

## 十、Git 工作流

```
main 分支：稳定版本（当前）
```

```bash
# 开发流程
git pull
git add -A
git commit -m "描述你的改动"
git pull --rebase
git push
```

### 当前 Git 远程

- **GitHub**：`https://github.com/Virukicy/GEHD`（Private）
- 本地仓库：`~/Desktop/GEHD项目/`

### .gitignore 关键规则

- `.workbuddy/` — AI 助手内部数据，绝不公开
- `GEHD_v36_工业化评审报告.md` — 内部评审材料
- `专家建议_从Python脚本到工业级幻觉核查软件.md` — 内部参考
- `config/*.json` — **已纳入版本控制**（配置文件应随代码一起发布）
