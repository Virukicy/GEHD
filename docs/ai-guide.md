# GEHD AI 代理 / 开发者参考手册

> **目标读者**：任何 AI 助手（Gemini/Claude/GPT/DeepSeek 等），需要操作 GEHD 进行文档幻觉核查  
> **前置阅读**：先读 [architecture.md](./architecture.md) 了解 GEHD 是什么  
> **版本**：v0.5.2  
> **最后更新**：2026-05-17

---

## 一、你（AI / 开发者）在 GEHD 生态中的角色

GEHD v0.5.1 的管道已全自动化。规则扫描、LLM 过滤、联网验证全部由引擎自动完成。你的角色不再是"手动验证"，而是：

1. **调用管道** — 选择合适的验证模式（full/fast/offline）
2. **消费结果** — 读取引擎输出的 issues/warnings/decision_log
3. **调优配置** — 根据结果反馈更新白名单/黑名单（可选）
4. **审计追溯** — 通过 --audit 或 GUI 审计视图追溯任意决策

```
你（AI/开发者）→ 选模式 → 管道全自动执行 → 结构化输出 → 你消费结果
```

---

## 二、快速开始

### 调用 GEHD

```bash
# 完整模式（规则+搜索+LLM 全链路，最高可信度）
python -m hallucination_checker document.docx --mode full

# 快速模式（规则+LLM 直接核验，零搜索成本）
python -m hallucination_checker document.docx --mode fast

# 离线模式（纯规则，零 API 成本）
python -m hallucination_checker document.docx --mode offline

# 审计模式（输出完整 decision_log JSON）
python -m hallucination_checker document.docx --audit
```

---

## 三、管道自动化工作流

GEHD v0.5.1 的管道是全自动的，不需要手动步骤。

### 基本流程

1. 选择验证模式（GUI 下拉框或 CLI --mode）
2. 引擎自动执行管道全链路
3. 结果在 GUI 全量展示或 CLI 终端输出
4. 如需追溯决策 → GUI 审计面板或 CLI --audit

### 管道内部流程（供理解，非操作步骤）

```
full 模式：
  规则引擎 → LLM 前置过滤 → 联网搜索(Tavily) → LLM 后置纠正 → 输出

fast 模式：
  规则引擎 → LLM 前置过滤 → LLM 直接核验(无搜索) → 输出

offline 模式：
  规则引擎 → 输出
```

### 读取结果

CLI 输出包含 issues（高危 ≥65 分）、warnings（中危 45-64 分）、stats（统计摘要）。

GUI 输出包含全文高亮、管道状态、审计视图（点击任意实体展开完整决策链）。

---

## 四、审计模式

### CLI 审计

```bash
python -m hallucination_checker document.docx --audit
```

输出完整 decision_log JSON，每条记录包含：时间戳、阶段名、输入候选数、输出候选数、决策类型、跳过原因。

### GUI 审计视图

设置窗口 → 管道状态栏 → 点击任意阶段 → 展开 decision_log 详情。

颜色编码：绿=通过，灰=跳过，红=异常。

---

## 五、管道模式选择指南

| 场景 | 推荐模式 | 原因 |
|------|:--:|------|
| 关键文档（合同/财报/研报） | full | 需联网核查确认实体真实性 |
| 批量初步扫描 | fast | LLM 直接核验，零搜索成本，速度快 10 倍 |
| 无网络环境 / 零成本 | offline | 纯规则引擎，准确率较低但零开销 |
| 需要完整审计追溯 | full 或 fast | decision_log 在任意非 offline 模式下均填充 |

---

## 六、JSON 配置修改注意事项

### 格式要求

- JSON 数组用方括号 `[]`，每个元素后加逗号（最后一个不加）
- JSON 字符串必须用双引号 `""`
- 修改前建议备份：`cp config/whitelist.json config/whitelist.json.bak`

### 验证 JSON 格式

```bash
python -c "import json; json.load(open('config/whitelist.json'))" && echo "OK"
```

### 不要改的文件

以下 JSON 中的 `_description`、`_usage`、`_note` 等以下划线开头的键是文档注释，不要删除：

- `thresholds.json` 中的 `"_high_note"`、`"_minimum_note"` 等
- `entity_patterns.json` 中的 `"_description"`、`"_usage"`
- 其他所有 `_` 开头的键

---

## 七、常见操作速查

| 你要做什么 | 操作 |
|------|------|
| 确认一个词真实存在 | → 加入 `config/whitelist.json` |
| 确认一个词是幻觉 | → 加入 `config/blacklist.json` |
| 正常词被误报为幻觉 | → 加入 `config/exclude_words.json` |
| 引擎太敏感（太多误报） | → 提高 `config/thresholds.json` 的 `high_threshold` |
| 引擎太松（漏报幻觉） | → 降低 `config/thresholds.json` 的 `high_threshold` |
| 新增一类实体检测 | → 在 `config/entity_patterns.json` 添加正则规则 |
| 写验证结果供下次参考 | → 更新 `_l4_cache.json` |

---

## 八、故障排查

| 症状 | 可能原因 | 解决 |
|------|------|------|
| 改了 JSON 不生效 | JSON 格式错误（逗号/引号） | 用 Python `json.load()` 校验 |
| 加了白名单词还报 | 子串匹配问题（2字词需前缀匹配） | 确认词长度和位置 |
| L4 队列为空 | 文档中无候选词或已改用 `--mode` | 检查 `--mode` 参数 |
| `ModuleNotFoundError` | 未安装依赖 | `pip install -e .` |
| `--verify` 不识别 | v0.5.0 后参数改为 `--mode` | 使用 `--mode full` 替代 |
