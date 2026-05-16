# GEHD — 文档幻觉核查工具

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.5.1-informational)](https://github.com/Virukicy/GEHD)
[![Tests](https://img.shields.io/badge/tests-127%2F127-brightgreen)](tests/)

基于**纯规则引擎**的轻量级文档幻觉核查工具。输入 `.docx` 文档，自动检测 AI 生成内容中可能被编造的专有名词、统计数据、引述和时间线。

> **核心理念**：不用 LLM 检查 LLM（"自己查自己"有致命缺陷），而是用**可审计、可解释**的正则 + 启发式规则。

---

## 快速开始

```bash
# 配置 API 密钥（联网核查 + LLM 功能必需）
cp config/secrets.json.template config/secrets.json

# 安装
pip install -e .

# 运行（支持 DOCX / TXT / MD / HTML / JSONL / CSV / PDF / PPTX）
python -m hallucination_checker document.docx

# 输出 L4 验证队列（含待联网核查清单）
python -m hallucination_checker document.docx --verify
```

<details>
<summary>示例输出</summary>

```
=================================================================
  DOCX 自检报告 v0.4.0-alpha (GEHD + L4联网核查)
=================================================================
  文件: report.docx
  段落: 50  |  表格: 0
=================================================================

  [!] 发现 2 个问题:
    1. [幻觉-L2] P38 虚构词 "母丑购": "有用户反映在母丑购购买..."

  [~] 11 个警告:
    1. [数据待核实] [可疑统计金额=48] P15 "80亿人民币"
    2. [一致性-高频实体] "辰星微电子"出现4次
    ...

  --- GEHD v0.4.0-alpha 统计 ---
  [L3] 实体候选: 16  (高危:0 中危:7 低危:9)
  [L2.5] 数据/引述候选: 4
=================================================================
```
</details>

---

## 核心能力

| 维度 | 检测内容 |
|------|------|
| **专有名词** | 疑似虚构的公司名、产品名、机构名、人名、地名 |
| **统计数据** | 无来源的大额金额、精确百分比、规模描述 |
| **引述** | 无法验证的权威人物引语、直接引语 |
| **时间线** | 未来日期、过于精确的事件时间声明 |
| **内部一致性** | 同一实体多处出现时上下文矛盾、同段落多金额共存 |

**输出**：0-100 分量化评分 → 高危 (≥65) / 中危 (45-64) / 低危 (<45) 三级分类。

**支持格式**：DOCX · TXT · MD · HTML · JSONL · CSV · PDF · PPTX

**GUI**：PySide6 桌面应用，含全文高亮视图、三套主题（默认/暗色/色盲友好）、管道状态栏、多模型交叉校验入口。启动：`python -m hallucination_checker.gui`

---

## 架构

可编排管道架构，LLM + 搜索双适配层：

```
📄 文件 → PipelineContext → L1-L4 规则引擎 → SearchAdapter → LLMAdapter → 📊 报告
```

详细架构请阅读 [docs/architecture.md](./docs/architecture.md)。

---

## 项目状态

- [x] **Iteration 1 完成** — 标准化项目结构、模块拆分、外部化配置
- [x] **Iteration 2 完成** — 类型安全/mypy/Ruff/logging/异常处理/125测试/85%覆盖率
- [x] **Iteration 3 完成** — P2-1 声明提取 + P2-2 适配层 + P2-3 联网核查 + P2-4 证据链 + P2-5 多模型交叉校验 + GUI 桌面应用

当前版本：**v0.5.1**

---

## 文档

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](./docs/architecture.md) | 架构全景：模块结构、数据流、配置系统、测试体系 |
| [docs/development.md](./docs/development.md) | 开发指南：环境搭建、运行测试、代码规范、修改场景 |
| [docs/ai-guide.md](./docs/ai-guide.md) | AI 代理操作指南：自迭代循环、配置修改、故障排查 |
| [docs/COLLABORATION.md](./docs/COLLABORATION.md) | 多智能体协作协议：文件域划分、Git 工作流、冲突处理 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更记录 |

---

## 许可

待定
