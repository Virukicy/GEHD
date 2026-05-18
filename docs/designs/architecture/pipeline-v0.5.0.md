> **归档** — 管道架构设计决策，所有实现细节已过时，仅供参考。

## 七、v0.5.0 展望 —— 可审计性基础设施

> v0.4.0 管道架构预留 `PipelineContext.decision_log: list[dict]` trace 字段，v0.5.0 实现完整决策追溯链。

### 7.1 为什么可审计性先于一切

v0.4.0 引入 LLM 管道后，GEHD 面临一个根本性矛盾：

- **规则引擎时代**：每个决策可追溯到具体正则匹配和评分公式 → 天然可审计
- **LLM 管道时代**：前置过滤和后置纠正都是黑盒 → **审计能力断崖式下降**

v0.5.0 的核心使命是**重新闭合审计链路**——让 LLM 管道的每一步决策都能被追溯。

### 7.2 交付范围 —— 两件事，非九件事

v0.5.0 看似需求多，实质归并为两个递进任务：

| 任务 | 负责 | 内容 | 先行条件 |
|------|:--:|------|------|
| **架构升级** | E | 契约式管道（STAGE + ADAPTER）+ 四层耦合全解 + 多路径 full/fast/offline | 无 |
| **审计链路** | E+U | decision_log 完整填充 + 审计视图（GUI）+ CLI --audit + 评分可解释性 | 架构升级完成 |

**为什么先架构后审计**：decision_log 的填充依赖契约式管道的阶段验证框架。架构不升级，decision_log 的填充没有标准化入口。

**交付清单**：

| 项 | 说明 |
|------|------|
| `decision_log` 完整填充 | 每个管道阶段向 context.decision_log 写入结构化 trace 条目（触发原因、输入、输出、置信度） |
| 审计视图（GUI） | 新建一个「审计」面板：选中任意候选实体 → 展开完整决策链 → 支持折叠/跳转/导出 |
| 评分可解释性增强 | 每个候选项的评分明细从隐式（代码内）变为显式（decision_log 中列出各维度加减分） |
| CLI 审计模式 | `--audit` 标志输出机器可读的完整 decision_log JSON，供外部审计工具消费 |

### 7.3 契约式管道架构 —— rc 故障链全量复盘

v0.4.0-rc 端到端验收触发 8 次修复，暴露信任式管道的结构性缺陷。以下将每个故障映射到契约式管道如何杜绝。

#### 7.3.1 rc 故障链（8 问题 → 3 类别）

| # | 问题 | 根因 | 类别 |
|:--:|------|------|:--:|
| 1 | L4 全哑 | `auto_verify` 键映射缺失（配置迁移断线） | 接线缺失 |
| 2 | LLM 完全未激活 | `gehd_check()` 未调用 `run_pipeline()` | 接线缺失 |
| 3 | CLI 未激活 LLM | CLI 入口未创建适配器 | 接线缺失 |
| 4 | GUI 未激活 LLM | GUI 入口未传 `llm` 参数 | 接线缺失 |
| 5 | 前置过滤静默跳过 | `context.candidates=[]` 硬编码为空 | 数据缺失 |
| 6 | 后置纠正静默跳过 | `search_result` 字段路径不匹配 | 字段不对齐 |
| 7 | HTTP 400 崩溃 | `import json` 在 try 内 + HTTPStatusError 未捕获 | 异常处理 |
| 8 | HTTP 400 持续 | `create_llm_adapter_from_config()` 读了 `llm.json.model` 但丢弃，回退到写死的 `gpt-4o` | **配置读后丢弃** |

#### 7.3.2 双层契约架构

v0.5.0 建立两层契约保护，全部在管道启动时一次性验证：

**第一层：STAGE_CONTRACTS — 管道阶段数据流验证**

每个阶段声明 `requires`（输入字段必须存在且非空）和 `produces`（输出字段名）。管道编排器在启动阶段前验证。

```python
STAGE_CONTRACTS: dict[str, dict] = {
    'llm_pre': {
        'requires': ['candidates'],
        # 杜绝 #5: candidates 为空 → 启动时判定跳过，写 decision_log，不静默
        'produces': ['candidates', 'decision_log'],
    },
    'llm_post': {
        'requires': ['l4_queue'],
        'requires_nested': ['l4_queue[*].search_result.snippets'],
        # 杜绝 #6: search_result.snippets 不存在 → 启动时告警
        'produces': ['decision_log'],
    },
    'web_verify': {
        'requires': ['l4_queue'],
        'produces': ['l4_queue'],
    },
    'cross_validate': {
        'requires': ['l4_queue'],
        'produces': ['decision_log'],
    },
}
```

**第二层：ADAPTER_CONTRACTS — 外部能力适配器配置验证**

每个外部能力声明必需的配置键和禁止的占位值。管道启动时全局验证，不等到 API 调用才 400。

```python
ADAPTER_CONTRACTS: dict[str, dict] = {
    'llm': {
        'requires_config': [
            'llm.json.model',
            'llm.json.base_url',
            'secrets.json.llm_api_key',
        ],
        'forbidden_values': {
            'llm.json.model': ['', 'gpt-4o'],
            # 杜绝 #8: model 不是空也不是占位值 → 必须在 llm.json 中显式配置
        },
        'forbidden_values_note': '占位值或空值在管道启动时直接报错',
    },
    'search': {
        'requires_config': [
            'search.json.provider',
            'secrets.json.tavily_api_key',
        ],
        'requires_config_note': '杜绝 #1: auto_verify 等键映射缺失 → 启动时验证',
    },
}
```

#### 7.3.3 管道启动时验证流程

`run_pipeline()` 在执行任何阶段前，先跑一轮契约检查：

```
1. ADAPTER_CONTRACTS 验证
   ├── 遍历每种外部能力
   ├── 检查 requires_config 中每个键是否存在于对应 JSON 文件中
   ├── 检查 forbidden_values 中是否有匹配的占位值
   └── 任一不通过 → 禁用对应阶段 + 写入 decision_log（不崩溃）

2. STAGE_CONTRACTS 验证（对每个开启的阶段）
   ├── 检查 requires 中每个字段在 context 中是否存在且非空
   ├── 检查 requires_nested 中嵌套路径是否可访问
   └── 不通过 → 跳过该阶段 + decision_log 记录原因

3. 执行阶段（验证通过后）
   └── 阶段函数不变，逻辑零改动
```

#### 7.3.4 故障 → 杜绝映射

| rc 故障 | 杜绝机制 |
|------|------|
| #1 auto_verify 键缺失 | ADAPTER_CONTRACTS.search.requires_config 启动时检查 |
| #2/#3/#4 接线缺失 | 管道启动验证：`pipeline.json` 开关为 true 则对应适配器必须非 None |
| #5 candidates 为空 | STAGE_CONTRACTS.llm_pre.requires → 启动时告警 |
| #6 search_result 字段不对齐 | STAGE_CONTRACTS.llm_post.requires_nested 嵌套验证 |
| #7 HTTP 400 崩溃 | JSON 容错加固（S2PM-009）+ adapter.chat() 异常标准化 |
| #8 model 默认值丢弃 | ADAPTER_CONTRACTS.llm.forbidden_values → 启动时报错 |

#### 7.3.5 四层耦合全解 + 多路径管道

v0.4.0 管道存在四层耦合，多路径（full/fast/offline）需要解耦后才能实现。v0.5.0 一并解决。

**当前四层耦合 → v0.5.0 解法**：

| 耦合 | 当前 | 解法 |
|------|------|------|
| ① pipeline → checker 直接 import + 解包 | `from .checker import _gehd_check_impl` + 解包 5 元组 | 规则引擎包装为注册阶段 `rules_engine`，pipeline 只知道「第一阶段」 |
| ② 硬编码阶段 if 块 | `if llm_pre → / if llm_post →` | STAGES 注册表 + 路径配置，阶段顺序可配 |
| ③ 共享可变 dict 无契约 | `context['candidates']` 谁都能读写 | STAGE_CONTRACTS.requires/produces + 启动时验证 |
| ④ post_filter → checker 内部函数 | 后置越过管道调用 `_feedback_l4_verdicts` | 提升到 pipeline 层，作为统一「后处理」步骤 |

**多路径管道**：解耦后支持三档验证模式，用户按需选择：

```
路径 A (mode='full', 高可信):
  rules_engine → llm_pre_filter → web_verify → llm_post_filter → 后处理

路径 B (mode='fast', 快速低成本):
  rules_engine → llm_pre_filter → llm_direct_verify → 后处理
                                    ↑ 纯 LLM 核验，跳过搜索

路径 C (mode='offline', 零成本):
  rules_engine → 后处理
  （就是 v0.3.0 纯规则模式）
```

`pipeline.json` 增加 `mode` 字段取代逐个开关的手动组合：
```json
{"mode": "full"}    // 或 "fast" / "offline"
```

**路径 B 新增阶段 `llm_direct_verify`**：不同于后置纠正的「对比两个文本」，而是凭 LLM 知识直接判断词的真实性。提示词：
> "根据你的知识，判断每个词在[类别]领域是否真实存在。返回 JSON"

**GUI 联动 + 根治 rc 闪退**：设置页增加「验证模式」下拉框（完整/快速/离线），替代当前独立开关的逐个勾选。管道阶段调度改为注册表遍历循环，每阶段开始前 emit 阶段名 → GUI 进度条实时显示「前置过滤中…」「后置验证中…」。**此改造直接根治 rc 阶段的进度假死闪退问题**——不再需要 rc 临时修补，v0.5.0 架构升级自然解决。

#### 7.3.6 改动范围（更新）

| 文件 | 改动 | 行数 |
|------|------|:--:|
| `engine/pipeline.py` | STAGE_CONTRACTS + ADAPTER_CONTRACTS + 阶段注册表 + `_validate_contracts()` + 多路径调度 | +80 |
| `engine/llm/` | 新增 `direct_verify.py`（LLM 直接核验阶段） | +50 |
| `engine/llm/adapter.py` | `create_llm_adapter_from_config()` 读取 model | 改 2 行 |
| `engine/checker.py` | `_feedback_l4_verdicts` 提升到 pipeline 层 | -20 |
| `config/pipeline.json` | 新增 `mode` 字段 | 改 3 行 |
| `gui/settings_dialog.py` | 验证模式下拉框 + 独立开关同步联动 | +15 |
| `gui/main_window.py` | 进度条实时阶段名 + 移除旧 cross_validate 独立路径 | +10 |
| 其他阶段文件 | **零改动** | 0 |

### 7.4 审计视图示例

用户在 GUI 中点击一个标记为「中危」的实体，审计面板展开：

```
📋 实体: "辰星微电子"  |  最终判定: 未通过（中危 60分）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [L3 规则评分]
  正则匹配: 半导体企业名 (基础分 45)
  形容词前缀: 无
  电商平台加分: +0
  频率加分: +10 (文档出现4次)
  可信字符降分: 0
  子串白名单: -0
  → 小计: 55

  [L3.6 一致性]
  高频实体标记: 是 (4次) → +3
  金额矛盾检查: 无
  → 小计: 58

  [L3.7 声明提取]
  匹配模式: 无声明性构造 → +2
  → 总分: 60 → 中危

  [LLM 前置过滤]
  判定: KEEP
  原因: 含"微电子"后缀，符合半导体公司命名模式

  [联网核查 - Tavily]
  结果: verified_real
  来源: 天眼查 "北京辰星微电子科技有限公司"
  日期: 2026-05-13

  [LLM 后置纠正]
  判定: 纠正 → verified_fake
  原因: 北京注册公司与文档上下文"完成B轮融资"不匹配
  置信度: 高
```

---

## 八、v0.6.0 展望 —— 自迭代闭环

> 引擎越用越聪明，用户越用越省心。

### 8.1 核心逻辑

v0.5.0 建立了审计安全网之后，可以安全地让引擎自动调整自身配置。

### 8.2 两档模式

| 模式 | 行为 | 适用用户 |
|------|------|------|
| **建议模式**（默认） | 引擎扫描 → 联网验证 → 自动判断应加白/黑名单 → **弹出建议，用户确认后生效** | 所有用户 |
| **自动模式**（可选开启） | 同上，但无需确认，直接写入配置 | 信任引擎准确率的进阶用户 |

### 8.3 交付范围

| 项 | 说明 |
|------|------|
| 配置建议引擎 | 基于 L4 联网核查结果自动判断：已验证真实 → 建议加白名单；已验证虚构 → 建议加黑名单；频繁误报 → 建议加排除词 |
| 建议审核 UI | GUI 设置页新增「待审核建议」面板：展示引擎建议的配置变更 → 逐条审批或批量通过 |
| 自动模式开关 | 设置页新增「自动学习」开关（默认关闭） |
| 审计保护 | 所有自动变更写入 decision_log，可在审计视图回溯 |

### 8.4 风险控制

- 自动模式仅影响白名单/黑名单/排除词三类配置，不动评分阈值和正则规则
- 每次自动变更前比对 `_l4_cache.json` 历史记录，避免反复横跳
- 所有变更可撤销（GUI 中一键回滚到上次手动确认的快照）

### 8.5 架构收尾 — 适配层真正可插拔

v0.4.0 宣称「双适配层同构架构，切换供应商零代码」。v0.5.0 审计显示当前状态为半解耦：

| 能力 | 换模型/后端 | 换供应商 | 缺口 |
|------|:--:|:--:|------|
| LLM | ✅ 改 `llm.json` | ⚠️ 需新 adapter 类 | `create_llm_adapter_from_config()` 硬编码返回 `OpenAIAdapter`，无 provider 注册表 |
| 搜索 | ✅ 改 `search.json` | ⚠️ 需新 backend + 改分发 | `TavilyBackend`/`DuckDuckGoBackend` 在 `l4_web_verify.py` 而非 `engine/search/`，无注册表 |

v0.6.0 收尾：

**1. Provider 注册表**（LLM + 搜索各一个）：
```python
LLM_PROVIDERS = {'openai': OpenAIAdapter, 'deepseek': OpenAIAdapter}
SEARCH_PROVIDERS = {'tavily': TavilyBackend, 'duckduckgo': DuckDuckGoBackend}
# 换供应商 = 加一行注册 + 写一个 adapter 类
```

**2. 搜索后端类搬家**：`TavilyBackend`/`DuckDuckGoBackend` 从 `l4_web_verify.py` 迁入 `engine/search/`，与 `SearchAdapter` 抽象基类同目录。
**3. 工厂函数改注册表驱动**：不再硬编码 class 名，从 `llm.json.provider` / `search.json.provider` 查注册表。

**改动量**：`l4_web_verify.py` -60 行 + `engine/search/` +60 行 + `adapter.py` 改 5 行。

### 8.6 QA 哨卡升级 — 从「代码不崩」到「功能不残」

#### 8.6.1 v0.5.0 暴露的问题

v0.5.0 闭环后 PM 持续发现功能级 bug：fast 模式 LLM 未激活、GUI 三模式 visible 错配、决策链被锁死在 full 模式。这些 bug 全部通过了 pytest/mypy/ruff 哨卡。

**根因**：当前 QA 哨卡只能保证「代码不崩」，不能保证「功能完整」。

| 当前检查 | 漏了什么 | v0.5.0 哪个 bug 穿过 |
|------|------|------|
| pytest 通过 | 无端到端用例 → fast 模式空跑看不出来 | fast 工厂漏 llm_direct_verify |
| mypy 零错误 | 不检测逻辑错误 → tooltip 写反了类型系统帮不了 | GUI 模式 visible 错配 |
| ruff 零错误 | 不检测功能完整性 | 决策链 locked to full |
| 文件域合规 | 不检测 E/U 产出是否对齐 | _pipe_mode vs STAGES 不对应 |

#### 8.6.2 升级内容

**新增三类哨卡检查**，与 pytest/mypy/ruff 并列：

| 关卡 | 检查什么 | 怎么验 | 谁 |
|------|------|------|:--:|
| **管道模式冒烟测试** | full/fast/offline 各跑一次 entity_spoof，验证产出非空 + 阶段日志完整 | 三条 CLI 命令，对比输出 | QA |
| **GUI 契约对齐检查** | settings_dialog 的 mode 值 → 对照 pipeline.py STAGES 注册表 → 验证可见性逻辑 | 读代码 + 跑 GUI 手动校验 | QA |
| **功能完整性检查表** | 对照 plan.md 交付清单，逐项勾验（非代码质量指标） | 人工 ± 自动化脚本 | QA |

#### 8.6.3 验收条件标准化

每个 plan.md 中的交付项，附带明确的验收条件，写入 PM2Q 指令：

```
v0.6.0 交付：自迭代建议引擎
  验收：
  ├── entity_spoof full 模式扫描 → decision_log 含 suggest_whitelist/suggest_blacklist
  ├── GUI 设置页出现「待审核建议」面板
  └── 手动确认一条建议 → whitelist.json 被正确更新
  谁验：QA
```

PM 不再自行逐个功能验证。QA 按验收条件执行，报告逐项通过/失败。

---

### 8.7 接口冻结纪律 — v0.5.0 架构革新的教训

#### 8.7.1 发生了什么

v0.5.0 为快速解决 v0.4.0 的技术债务和接线噩梦，通过架构革新（契约式管道 + 多路径）一次性重写了管道调度层。但忽略了一个关键前提：**接口冻结**。

```
v0.4.0-beta 的成功模式（接口先冻结，E/U 再并行）：
  E 冻结 PipelineContext + pipeline.json → U 按契约开发 → 一次对齐 ✅

v0.5.0 的失败模式（E/U 同时动，互相等）：
  E 改 STAGES 注册表 → U 改 settings_dialog mode 映射
  → E 改 decision_log 结构 → U 改 DecisionTraceDialog 解析
  → 三模式同时暴露，E 和 U 反复排查对齐
  → 决策链被锁死在 full 上，fast/offline GUI 改了又改 ❌
```

**根因**：小架构革新（管道逻辑梳理清楚）带动大架构混沌（GUI 协同完全没跟上）。前后端同时变动，没有提前做接口设计，接口冻结步骤被跳过。

#### 8.7.2 v0.6.0 纪律

任何跨 E/U 的功能，强制执行「先冻结，后并行」：

| 步骤 | 谁 | 做什么 | 冻结物 |
|:--:|:--:|------|------|
| 1 | E | 完成接口定义，写入 `workspace/E/interface-{version}.md` | 字段名、类型、示例值 |
| 2 | S | 审阅接口，确认与 plan.md 一致 | — |
| 3 | PM | PM→U 下发冻结后的接口文档 | — |
| 4 | E+U | 并行开发，E 不改接口，U 只读冻结版本 | 冻结物不可变 |
| 5 | QA | 按接口文档验证 E/U 产出对齐 | — |

**铁律**：步骤 3 完成前，U 不动代码。步骤 3 完成后，E 不改接口。任何接口变更 → 重新走步骤 1-3。