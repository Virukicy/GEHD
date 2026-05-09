# GEHD AI 代理操作指南

> **目标读者**：任何 AI 助手（Gemini/Claude/GPT/DeepSeek 等），需要操作 GEHD 进行文档幻觉核查  
> **前置阅读**：先读 [architecture.md](./architecture.md) 了解 GEHD 是什么  
> **最后更新**：2026-05-09

---

## 一、你（AI）在 GEHD 生态中的角色

GEHD 是一个**半自动**幻觉核查工具。引擎负责扫描文档、标记可疑内容，但**你（AI）负责验证**。

```
GEHD 引擎  →  输出候选列表（issues/warnings/L4队列）
     ↓
你（AI）   →  联网搜索验证候选词是否真实存在
     ↓
用户反馈   →  "这个词确实存在" / "这个词是编的"
     ↓
你（AI）   →  根据反馈更新配置（白名单/黑名单等）
     ↓
GEHD 引擎  →  下次扫描时自动加载更新后的配置
```

**核心原则**：GEHD 不会自己上网验证，不会自己更新配置。这两个动作都需要你来做。

---

## 二、快速开始

### 调用 GEHD

```bash
# 标准扫描（输出到终端）
python -m hallucination_checker <文档路径>.docx

# 完整扫描 + L4 验证队列导出为 JSON
python -m hallucination_checker <文档路径>.docx --verify
```

`--verify` 模式会在文档同目录生成 `_l4_queue.json`，包含所有待验证的候选词。

### 读取 L4 验证队列

```python
import json

with open("文档路径_l4_queue.json", "r", encoding="utf-8") as f:
    queue = json.load(f)

# 高危候选（≥65分）→ 优先验证
deep_items = [q for q in queue["entities"] if q["score"] >= 65]

# 中危候选（45-64分）→ 次优先
medium_items = [q for q in queue["entities"] if 45 <= q["score"] < 65]
```

---

## 三、标准工作流（自迭代循环）

### 第 1 步：扫描文档

```bash
python -m hallucination_checker report.docx --verify
```

### 第 2 步：读取结果

```
[幻觉-L3高危] P17 [半导体企业名=60] "辰星微电子" ctx:"...辰星微电子宣布完成..."
[数据-L2.5高危] [可疑统计金额=48] P15 "80亿人民币"
[实体待核实] P31 [电商平台名=60] "灵犀购"
```

### 第 3 步：联网验证每个候选词

对 L4 队列中的每个候选词：

```
候选词: "辰星微电子"
搜索: site:crunchbase.com OR site:tianyancha.com "辰星微电子"
结果: 无任何结果 → 判定为 虚构/幻觉
```

```
候选词: "灵犀购"
搜索: "灵犀购" 电商
结果: 无任何结果 → 判定为 虚构/幻觉
```

```
候选词: "80亿人民币"
搜索: [公司名] 融资 80亿
结果: 无相关报道 → 判定为 无法验证（need_manual_check）
```

### 第 4 步：写入验证缓存

```bash
# 读取已有缓存（如果有）
cat 文档路径_l4_cache.json

# 更新缓存（添加验证结果）
```

缓存格式（`_l4_cache.json`）：

```json
{
  "verified_entities": [
    {
      "word": "辰星微电子",
      "verdict": "verified_fake",
      "evidence": "天眼查/Crunchbase均无此公司记录",
      "verified_at": "2026-05-08T23:00:00"
    },
    {
      "word": "华为",
      "verdict": "verified_real",
      "evidence": "https://www.huawei.com - 知名企业",
      "verified_at": "2026-05-08T23:00:00"
    }
  ]
}
```

verdict 枚举：
- `verified_real` — 已确认真实存在
- `verified_fake` — 已确认为幻觉（虚构）
- `need_manual_check` — AI 无法自动判定，需人工
- `unable_to_verify` — 信息不足，无法验证

### 第 5 步：更新配置（自迭代核心）

根据验证结果编辑 `config/` 下的 JSON 文件：

**加白名单**（词真实存在，以后直接放行）：

编辑 `config/whitelist.json`，在 `whitelist` 数组中添加：

```json
{
  "whitelist": [
    ...现有词...,
    "新确认的公司名",
    "新确认的产品名"
  ]
}
```

**加黑名单**（词确认为幻觉，以后直接拦截）：

编辑 `config/blacklist.json`，在 `blacklist` 数组中添加：

```json
{
  "blacklist": [
    ...现有词...,
    "新发现的幻觉词"
  ]
}
```

**加排除词**（正常词被误报，以后跳过）：

编辑 `config/exclude_words.json`，在 `exclude_words` 数组中添加。

### 第 6 步：重新扫描（验证自迭代效果）

```bash
python -m hallucination_checker report.docx --verify
```

更新后的配置自动生效，之前确认的问题不再重复报告。

---

## 四、JSON 配置修改注意事项

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

## 五、常见操作速查

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

## 六、故障排查

| 症状 | 可能原因 | 解决 |
|------|------|------|
| 改了 JSON 不生效 | JSON 格式错误（逗号/引号） | 用 Python `json.load()` 校验 |
| 加了白名单词还报 | 子串匹配问题（2字词需前缀匹配） | 确认词长度和位置 |
| L4 队列为空 | 文档中无候选词或 `--verify` 未加 | 检查命令行参数 |
| `ModuleNotFoundError` | 未安装依赖 | `pip install -e .` |
