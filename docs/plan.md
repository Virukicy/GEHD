# GEHD v0.4.0 路线图 —— 智能管道

**日期**: 2026-05-12  
**作者**: PM  
**状态**: 已批准

---

## 一、主题

> 从纯规则引擎到规则+可组合智能过滤。每位用户自主选择管道深度。

---

## 二、版本路线

```
v0.4.0-pre  →  v0.4.0-alpha  →  v0.4.0-beta  →  v0.4.0-rc  →  v0.4.0
  (S+D)          (E 管道)        (E前置+U UI)     (E后置+QA)     (D+QA终局)
```

---

## 三、逐版本详解

### v0.4.0-pre — S 组入场 + 开发计划文档（S + D）

| 项 | 执行方 | 说明 |
|------|:--:|------|
| S 组建立 | PM | 创建 `workspace/S/`，S 开始履职 |
| 协作协议更新 | D | COLLABORATION.md 新增 S 组（六方协作） |
| 开发计划文档 | D→S | D 在 `workspace/S/` 创建 `development-plan.md`，写入本路线图。此后由 S 维护 |
| 协议赋权 | D | S 拥有建议权，不拥有调度权。S → PM → 执行组 |

**验收**：COLLABORATION.md 含 S 组。`workspace/S/development-plan.md` 存在且内容完整。S 可独立产出 S2PM 传递文档。

**API 消耗**：0。

---

### v0.4.0-alpha — 管道基础设施（E）

核心原则：**重构不重写。** 现有代码装进管道框架，行为一行不变。

| 项 | 文件 | 说明 |
|------|------|------|
| 管道编排器 | `engine/pipeline.py` | `run_pipeline(text, config, llm?)`，链式调用 |
| 配置拆分 | `config/pipeline.json` | 五个开关，从 `thresholds.json` 迁移 |
| | `config/llm.json` | LLM 供应商/模型/温度，不含 Key |
| | `config/search.json` | 搜索后端，从 `thresholds.l4` 迁移参数 |
| | `config/thresholds.json` | 精简，`l4` 块移除（旧键保留 DeprecationWarning） |
| LLM 适配层 | `engine/llm/` | `LLMAdapter` 抽象 + `OpenAIAdapter`（兼容 DeepSeek） |
| 搜索适配层 | `engine/search/` | `SearchAdapter` 抽象 + `TavilyAdapter` + `DuckDuckGoAdapter`（与 LLM 适配层同构） |
| 管道标准化中间格式 | `engine/pipeline.py` | `PipelineContext` TypedDict，统一各环节数据交换格式（L1-L3.7 输出、L4 核查结果、交叉校验共识均装入同一结构） |

**验收**：120 测试全绿。纯规则模式下行为与 v0.3.0 完全一致。PipelineContext 数据流通过类型检查。

**API 消耗**：0（纯规则 + mock 测试）。

---

### v0.4.0-beta — LLM 前置 + GUI 管道（E + U）

**E 侧**：

| 项 | 说明 |
|------|------|
| `engine/llm/pre_filter.py` | 批量去噪：一次 API 调分拣候选 → 返回保留列表 |
| pipeline 接线 | `config.llm_pre_filter=true` 时启动 |
| `config/secrets.json` | 新增 `llm_api_key` |
| LLM 前置校准机制 | `_l4_cache.json` 中标注 `must_retain: true` 的关键实体 → 前置过滤后检查是否被误删 |
| 配置自动迁移 | `thresholds.json` 旧 `l4` 块首次加载时自动迁移到 `search.json`，写入 `.migrated` 标记，用户零感知 |

**U 侧**：

| 项 | 说明 |
|------|------|
| 管道选项卡 | 设置窗口新增，替代当前 L4 选项卡 |
| 管道状态栏 | 主界面底部 |
| LLM 配置 UI | 供应商 + 模型 + API Key 输入 |

**验收**：entity_spoof 扫描，`l4_auto_verify=False`，LLM 前置开启 → L4 队列候选数从 19 降到 ≤8，且所有 `must_retain` 实体未被误删。配置自动迁移（旧 `l4` 块 → `search.json`）生效。

**API 消耗**：0（LLM 前置不触发 Tavily，QA 只做代码审查 + L4 队列数验证）。

---

### v0.4.0-rc — LLM 后置 + 端到端验证（E + QA）

| 项 | 说明 |
|------|------|
| `engine/llm/post_filter.py` | 语义判断：读 Tavily 结果上下文 → 纠正误判 |
| H01 回归 | Tavily 已有缓存喂给 LLM 后置 → 验证纠正 verified_fake |
| QA 验收 | entity_spoof 单文档全管道（≤3 次 Tavily） |

| 模型漂移校准集 | entity_spoof 选 5 个关键候选（3 应保留 + 2 应过滤），LLM 管道运行后 QA 手动比对一致性 |

**验收**：H01 "华为辰星科技" 从 verified_real 纠正为 verified_fake。校准集 5/5 通过。

**API 消耗**：≤3 次 Tavily（仅 entity_spoof 一份文档一次全管道）。

---

### v0.4.0 — 终局（D + QA）

| 项 | 执行方 | 说明 |
|------|:--:|------|
| M5 全量回归 | QA | 使用 β/RC 阶段缓存数据，不触发新 Tavily |
| 文档同步 | D | architecture.md 管道架构 + CHANGELOG v0.4.0 |
| PM 决策存档 | PM | 第四轮闭环 |

**API 消耗**：0。

---

## 四、API 消耗管控

| 版本 | Tavily 调用 | 策略 |
|------|:--:|------|
| pre | 0 | 纯文档，不触发引擎 |
| alpha | 0 | mock + 纯规则测试 |
| beta | 0 | LLM 前体验收看队列数，不跑 Tavily |
| rc | ≤3 | 仅一次端到端确认 |
| final | 0 | 缓存回归 |
| **合计** | **≤3** | 对比 M3-M5（~200 次），节省 98%+ |

---

## 五、协作分工

| 版本 | E | U | QA | D | S |
|------|:--:|:--:|:--:|:--:|:--:|
| pre | — | — | — | ✅ | ✅ |
| alpha | ✅ | — | — | — | — |
| beta | ✅ | ✅ | ✅ | — | — |
| rc | ✅ | — | ✅ | — | — |
| final | — | — | ✅ | ✅ | — |

---

## 六、v0.5.0 展望 —— 可审计性基础设施

> v0.4.0 管道架构预留 `PipelineContext.decision_log: list[dict]` trace 字段，v0.5.0 实现完整决策追溯链。

**方向**：GEHD 核心差异化——「可审计、可解释」——延伸为每个决策点的结构化追溯：

```
候选 "辰星微电子" 评分 60（中危）→
  LLM前置: KEEP（原因: 含"微电子"后缀，半导体公司命名模式）→
  联网核查: verified_real（来源: Tavily "北京辰星微电子科技有限公司"）→
  LLM后置: 纠正→verified_fake（原因: 北京注册公司与文档上下文"B轮融资"不匹配）
```

**设计原则**：v0.4.0 仅预留 `decision_log` 字段（不实现逻辑），确保管道架构为审计能力留好接口，避免 v0.5.0 时重构。

---

_审批: PM。执行顺序已确定。最后更新: S (2026-05-13)。_
