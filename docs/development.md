# GEHD 开发指南

> **版本**：v0.2.0  
> **最后更新**：2026-05-09  
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

# 2. 安装依赖（方式一：pip）
pip install -e .

# 2. 安装依赖（方式二：Poetry，推荐）
# pip install poetry
# poetry install

# 3. 运行
python -m hallucination_checker path/to/document.docx
python -m hallucination_checker path/to/document.docx --verify  # 含 L4 队列
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
from hallucination_checker.engine.checker import gehd_check

issues, warnings, stats, l4_queue = gehd_check(doc, output_verify_queue=True)
```

- `issues: list[str]` — 高危问题（≥65 分）
- `warnings: list[str]` — 中低危警告（45-64 分）
- `stats: dict` — 统计信息（候选数、分级计数等）
- `l4_queue: list[dict]` — L4 待联网验证队列

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
# 标准检查
python -m hallucination_checker document.docx

# 输出 L4 验证队列（JSON）
python -m hallucination_checker document.docx --verify
```

### 运行测试

```bash
# 全量回归测试
pytest tests/test_regression.py -v

# 预期：18 passed
```

**注意**：测试依赖 `GEHD_RedTeam_v2_Document.docx`，路径见 `tests/conftest.py`。

### 测试覆盖范围

| 测试类 | 测试数 | 覆盖层 |
|------|------|------|
| `TestL2Blacklist` | 2 | L2 黑名单 |
| `TestL1Whitelist` | 2 | L1 白名单 |
| `TestL3EntityDetection` | 3 | L3 实体检测 + 评分 |
| `TestL25NonEntityDetection` | 2 | L2.5 非实体检测 |
| `TestL36ConsistencyCheck` | 1 | L3.6 一致性 |
| `TestL4QueueOutput` | 3 | L4 队列协议 |
| `TestV36QuoteTighteningRegression` | 1 | 引语收紧回归 |
| `TestL4ProtocolStructure` | 1 | L4 JSON 协议完整性 |
| `TestEdgeCases` | 3 | 边界条件 |

### 测试升级路线（P1-5 详细计划）

**当前问题**：18 个测试全是回归测试（依赖外部 docx 文件），无独立单元测试，覆盖率约 30%。

**阶段 A — Iteration 2 内完成**：新增 ~30 个纯函数单元测试

| 测试类 | 内容 | 新增数量 |
|------|------|------|
| `TestL1WhitelistUnit` | 白名单精确匹配、子串匹配（2字/3字+）、剩余长度判定 | ~8 |
| `TestL2BlacklistUnit` | 黑名单命中/未命中/部分匹配 | ~4 |
| `TestL3ScoringUnit` | 评分各维度独立验证（基础分/形容词降分/频率加分/可信字符降分） | ~10 |
| `TestL36ConsistencyUnit` | 高频检测阈值、金额矛盾单/多段落 | ~4 |
| `TestConfigLoading` | JSON 加载正确性、回退默认值、未知 key 警告 | ~5 |

注：阶段 A 的测试不依赖外部 docx 文件，全部基于构造的字符串输入。

**阶段 B — Iteration 3 前完成**：

- 构造对抗样本 docx（白名单子串绕过、中英文混合、超长文本）
- 边界输入测试（空文档、纯数字、纯英文）
- 性能基准测试（500+ 段落大文档耗时）

---

## 四、代码规范

### 模块命名

```
engine/layers/l1_whitelist.py   — L1 层：白名单放行
engine/layers/l2_blacklist.py   — L2 层：黑名单拦截
engine/layers/l25_nonentity.py  — L2.5 层：非实体幻觉
engine/layers/l3_heuristic.py   — L3 层：启发式评分
engine/layers/l36_consistency.py — L3.6 层：一致性检查
engine/layers/l4_verify.py      — L4 层：验证队列
```

### 类型注解（进行中）

- 引擎层（`engine/layers/`）：**有**完整类型注解
- IO 层（`io/`）：**部分**有——返回类型有，参数 `doc` 缺（P1-1 待修）
- CLI 层：**有**完整类型注解

### 不允许的做法

- ❌ `except Exception` 宽泛捕获（除非有 `raise` 重新抛出）
- ❌ `globals()` 或 `exec()` 魔法赋值（v0.1.1 已重构）
- ❌ 硬编码魔术数字（v0.1.2 已提取 `DEEP_SEARCH_THRESHOLD`）
- ❌ 跨层直接读取其他层的内部变量（必须通过函数接口）

---

## 五、关键设计决策

### 为什么是纯规则引擎而非 LLM？

LLM 自查有致命缺陷——模型无法判断自己生成的内容是否为幻觉（"自己检查自己"）。GEHD 用纯正则 + 启发式规则，结果可审计、可解释、不依赖任何单一模型。

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

| 编号 | 问题 | 状态 |
|------|------|------|
| M1 | `io/format_checks.py` 函数参数缺类型注解 | ✅ P1-1 已修复 |
| M2 | 候选实体使用裸 `dict`，无 `TypedDict` | ⏳ 待处理 |
| M5 | 去重逻辑在两处重复 | ⏳ 待处理 |
| R7 | 缺少 `.editorconfig` | ✅ P1-2 已修复 |
| R8 | `config.py` 使用四层 `parent` 相对路径 | ✅ P1-0 已修复（parents[3]） |
| — | `scorers/` 目录为空壳 | ⏳ 待处理 |
| — | 测试覆盖率不足（仅回归测试，无单元测试） | ✅ P1-5 已修复（27 单元测试，85%） |

### 设计决策：print vs logging

终端用户输出保持 `print()`，内部诊断使用 `logging` 写 `gehd.log`。
原因：`StreamHandler` 绑定对象引用而非变量名，测试框架替换 `sys.stdout` 时无法跟随。
功能零损失——日志含时间戳和结构化消息，满足审计需求。

---

## 八、Git 工作流

```
main 分支：稳定版本（当前）
```

```bash
# 开发流程
git add -A
git commit -m "描述你的改动"
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
