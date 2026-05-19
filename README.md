# GEHD — Generalized Entity Hallucination Detection

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)](https://github.com/Virukicy/GEHD)
[![Version](https://img.shields.io/badge/version-0.5.2-informational)](https://github.com/Virukicy/GEHD)
[![Tests](https://img.shields.io/badge/tests-127%2F127-brightgreen)](tests/)
[![Built with](https://img.shields.io/badge/Built%20with-WorkBuddy%20Six‑Agent%20Protocol-8A2BE2)](docs/COLLABORATION.md)

> **这是我的第一个软件项目。我没有任何计算机背景。我没开过 IDE，没写过一行代码。**
>
> GEHD 的每一行 Python、每一个配置文件、每一个测试用例，都由 AI 智能体在六方协作协议下独立编写。我只做了一件事：**决策和沟通**。

基于规则 + LLM + 搜索三层管道的文档幻觉核查工具。输入 `.docx` 文档，自动检测 AI 生成内容中可能被编造的专有名词、统计数据、引述和时间线。

**人和 AI 都能操作它**：人类通过 PySide6 桌面 GUI 直观核查；AI 智能体通过 CLI 命令行批量接入——两类使用者共用同一管道引擎，**人类审阅界面中的每个操作，AI 都能通过相同的 API 自主执行**。

**不知道怎么操作？把 [docs/ai-guide.md](./docs/ai-guide.md) 丢给你的 AI 助手，它能自己读、自己操作 GEHD。** 整份文档就是为 AI 智能体写的——它不假设读者是人类。

---

## 这个项目证明了什么

GEHD 是一个软件产品，但它的**真正价值不是代码**——它证明了：

| 命题 | 证据 |
|------|------|
| **软件开发正在变得更可访问** | 一个零背景的普通人，仅凭结构化沟通和 AI 智能体，交付了全栈软件 |
| **AI 智能体可以组成有效团队** | 六方角色（E/U/QA/D/PM/S）按固定协议协作，不输人类团队 |
| **写出好代码不需要顶级模型** | 全程 DeepSeek V4 Flash——最便宜的模型之一。Claude、Gemini、GPT 一个没用过。不是堆算力换质量，是 SOP 换质量 |
| **管理优于编码** | 核心技能不是写代码，是：定标准 → 下指令 → 验结果 → 闭环 |
| **这套方法论是可复用的** | 协作基底在 10 分钟内迁移到下一个项目，完整就绪 |

---

## 它是怎么被造出来的

不是「我写代码，AI 辅助」。是：

```
我（人类）            ← 决策、方向、审阅
  ↓
PM 智能体             ← 调度、流程、闭合
  ↓          ↓  ↓  ↓
E  ·  U  ·  QA  ·  D  ·  S   ← 各司其职的执行体
```

- 我从没打开过 VS Code
- 我从没敲过 `git commit`
- 我从没手动改过一行 `.py` 文件
- 所有工作都在 WorkBuddy 的聊天界面完成，指令格式就是自然语言 + 传递号
- 全过程使用 **DeepSeek V4 Flash**——最便宜的模型之一，从没用过 Claude、Gemini、GPT

整个项目的「基建」是一套 5,000 字的协作协议（`docs/COLLABORATION.md`），定义了身份卡制度、无检测不管理原则、三段闭环流程。这套协议和代码一起交付，可以迁移到任何新项目。

---

## 快速开始

> **当前仅支持 macOS。** 项目在 macOS 上开发和测试，Python 3.11+ 可运行。Windows/Linux 移植未完成（GUI 主题和路径处理需跨平台适配）。

```bash
# 1. 克隆
git clone https://github.com/Virukicy/GEHD.git
cd GEHD

# 2. 配置 API 密钥（联网核查 + LLM 功能必需）
cp config/secrets.json.template config/secrets.json
# 然后编辑 config/secrets.json，填入你的 DeepSeek 和 Tavily API Key

# 3. 安装（推荐全量安装，含 GUI + 联网 + 多格式）
pip install -e ".[all]"

# 4. 运行
#   → CLI 模式（适合 AI 智能体批量接入）
python -m hallucination_checker document.docx --mode full
#   → GUI 模式（适合人类直观操作）
python -m hallucination_checker.gui
```

<details>
<summary>示例输出</summary>

```
=================================================================
  DOCX 自检报告 v0.5.2 (GEHD 管道模式)
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

  --- GEHD v0.5.2 统计 ---
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

**GUI**：PySide6 桌面应用，含全文高亮视图、三套主题（默认/暗色/色盲友好）、管道状态栏、多模型交叉校验入口。

---

## 架构

可编排管道架构，LLM + 搜索双适配层：

```
📄 文件 → PipelineContext → L1-L4 规则引擎 → SearchAdapter → LLMAdapter → 📊 报告
```

三路径模式：
- **full** — 全管道（规则 + LLM + 联网搜索）
- **fast** — 仅规则引擎（离线，零 API 消耗）
- **offline** — 规则引擎 + LLM 前置过滤

详细架构请阅读 [docs/architecture.md](./docs/architecture.md)。

---

## 协作协议

GEHD 真正的核心产出——`docs/COLLABORATION.md`：

| 制度 | 一句话 |
|:--:|------|
| **身份卡** | 每次调度告诉 AI：「你是谁、你能碰什么、你不能碰什么」 |
| **无检测不管理** | 下指令的同时写下验收命令，没通过就是没做完 |
| **三段闭环** | PM → 执行组 → QA → PM，品质不是自检出来的，是独立验出来的 |
| **短指令词典** | 「D2PM」= 看 D 组的回执，「闭合」= 收尾流程 |
| **文档即契约** | 每个指令有固定模板，AI 不看上下文也能知道该干什么 |

详细协议见 [docs/COLLABORATION.md](./docs/COLLABORATION.md)。

---

## 项目历程

| 阶段 | 关键交付 |
|:--:|------|
| **基底** | 项目结构标准化、配置外化、身份卡制度建立 |
| **管道** | 三层管道架构、双适配层、审计链路 |
| **流程** | 无检测不管理、CI 角色设计、上下文连续性纠正 |
| **归档** | 文档结构清理、全量索引同步 |
| **交接** | 协作系统模板化迁移至新项目，正式交接信 |

---

## 文档

| 文档 | 内容 |
|------|------|
| [docs/architecture.md](./docs/architecture.md) | 架构全景：模块结构、数据流、配置系统、测试体系 |
| [docs/development.md](./docs/development.md) | 开发指南：环境搭建、运行测试、代码规范、修改场景 |
| [docs/ai-guide.md](./docs/ai-guide.md) | 开发者参考手册：管道调用、审计模式、故障排查 |
| [docs/COLLABORATION.md](./docs/COLLABORATION.md) | 🎯 **核心产出**：多智能体协作协议 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更记录 |

---

## 致谢

GEHD 由 **WorkBuddy Six-Agent Protocol** 驱动。六方 AI 智能体（E/U/QA/D/PM/S）在人类决策和 SOP 框架下协作完成全部工作。

项目的发起人（齐）在项目期间没有编写任何代码——他负责的是：方向判断、指令质量、验收审核、流程闭环。

> *"If you can communicate clearly, you can build software."*

---

## 许可

[MIT](./LICENSE)
