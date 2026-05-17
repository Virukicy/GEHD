# 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) (SemVer 2.0)。

## [0.3.0] — 2026-05-12

### Iteration 3 完成 — 壁垒化 + 团队化

#### 新增
- L3.7 声明提取 — 6 类声明性构造检测
- L4 联网自动核查 — Tavily + DuckDuckGo 双后端，auto 模式智能切换
- L4 判决反写 — verified_fake 升级 issue，verified_real 移除 warning
- P2-4 证据链 — 四段结构（scoring/consistency/verification/recommendation）
- P2-5 多模型交叉校验 — 三路并行 + 强/弱/分歧共识
- GUI 桌面应用 — PySide6 全功能（QThread 异步扫描 + 交叉校验入口）
- 五方协作协议 — E/U/QA/D/PM，文件域分治，传递文档体系
- 7.6 执行证据标准 — 防止多智能体 LLM 伪造回执

#### 修复
- GUI 设置窗口无法打开
- GUI 联网核查闪退（同步 HTTP 阻塞主线程）
- L4 DuckDuckGo 中国大陆不可达

#### 质量
- 测试: 120/120
- mypy: 零错误
- ruff: 零错误
- L4 反写清理率: 80%（Warnings 108→22）

## [0.5.2] — 2026-05-17

### 协作体系
- 传递文档内部结构标准化（六字段头部 + A/B/C 类别）
- 身份卡注入制度（PM 每次调度携带）
- PM 短指令词典（PM2D / D回执 等）
- D 组 Git 标准化流程
- 接口冻结纪律 §7.8
- S 组正式入协（战略规划 → PM 审批流）

### 架构
- 用户数据目录 XDG 分离 (~/.gehd/)

---

## [0.5.1] — 2026-05-15

### 审计
- decision_log 全链路审计
- CLI --audit 命令
- GUI 审计视图

### 日志
- gehd.log 结构化日志系统

---

## [0.5.0] — 2026-05-14

### 管道架构
- 契约式管道：PipelineContext + 双层契约
- 三路径模式：full / fast / offline
- 管道编排器：四阶段注册（rules_engine → llm_post_filter → search_adapter → llm_adapter）
- LLMAdapter + SearchAdapter 双适配层解耦

### 修复
- v0.4.0-rc 全部 8 类故障（接线缺失/数据缺失/字段不对齐/配置读后丢弃）

---

## [0.4.0] — 2026-05-13

### 新增
- 管道编排器（PipelineOrchestrator）
- LLM 适配层（DeepSeek）
- SearchAdapter 抽象层（Tavily / DuckDuckGo / 离线占位）
- 配置三分层（thresholds / pipeline / llm）
- GUI 管道选项卡 + 模式切换
- S 组首次入场（战略规划）

---

## [0.4.0-rc] — 2026-05-13
- LLM 后置纠正 + 端到端验收

## [0.4.0-beta] — 2026-05-13
- LLM 前置过滤 + GUI 管道选项卡

## [0.4.0-alpha] — 2026-05-13
- 管道编排器 + LLM 适配层初版

---

## [0.3.1] — 2026-05-12

### 新增
- IO 七种新格式支持（TXT/MD/HTML/JSONL/CSV/PDF/PPTX）
- GUI 全文高亮视图
- GUI 三套主题系统（默认/暗色/色盲友好）
- GUI 管道状态栏
- L4 搜索后端 Tavily 集成（Tavily + DuckDuckGo 双后端 auto 智能切换）

### 修复
- L4 DuckDuckGo 中国大陆不可达
- GUI 设置窗口无法打开
- GUI 联网核查闪退（同步 HTTP 阻塞主线程）

---

## [0.3.0-alpha] — 2026-05-09

### Iteration 3 完成

- **P2-1**: L3.7 声明提取模块 — 6类声明性构造检测，semantic doc 0→5 issues
- **P2-5**: 多模型交叉校验 — 三路并行 + 强/弱/分歧共识模型
- **P2-4**: 证据链生成 — 四段结构 (scoring/consistency/verification/recommendation)
- **P2-3**: L4 联网自动核查 — DuckDuckGo 两阶验证, 4种结果标签
- **P2-2**: 适配层补全 — from_text / from_markdown 工厂方法
- 配置外置化扫尾 — L3 硬编码列表迁入 thresholds.json (l3_behavior)
- GUI 桌面应用 — PySide6 全功能交付
- 协作协议 — 五方协作（E/U/QA/D/PM）

### 质量指标
- 测试: **114/114**
- ruff: **零错误**
- M2 验收: semantic ≥1 ✅, benchmark 0 issues ✅

---

## [0.2.0] — 2026-05-09

### Iteration 2 完成 — 工程化提升

- **P1-0**: GEHDConfig dataclass 重构 — 30+全局变量→单一配置数据类，删除 _apply_external_config 等 90 行机械代码
- **P1-1**: 全量类型注解 — mypy 22 文件零错误，TYPE_CHECKING 模式导入 Document 类型
- **P1-2**: Ruff 格式化 + lint — 16 文件格式化，25 lint→0，新增 .editorconfig
- **P1-3**: logging 文件日志 — gehd.log 含时间戳和结构化消息，终端输出保持 print()（测试兼容）
- **P1-4**: 异常处理标准化 — except Exception→精确类型（ValueError/OSError/JSONDecodeError）
- **P1-5**: 单元测试 — 27 新测试，总测试 45，覆盖率 30%→85%

### 质量指标
- 测试: **97/97** (27 单元 + 18 回归)
- mypy: **零错误** (22 文件)
- ruff: **零错误**
- 覆盖率: **85%**

---

## [0.1.2] — 2026-05-08

### 修复
- 消除魔术数字 55，新增 DEEP_SEARCH_THRESHOLD 常量（N4）
- 删除死函数 check_whitelist()（N3）
- 删除死常量 SCORE_ECOMMERCE_EXTRA（N5）
- 未知阈值键触发 UserWarning（N2），顺便修复 adjective_penalty 从未从 JSON 加载的隐藏 bug
- _apply_thresholds 中 _mapping dict → _valid_keys set（N1）
- 测试文档版本号更新（N6）
- 删除死 except KeyError（M4）
- engine/__init__.py 标注 scorers 状态（M8）

### 安全
- 从 Git 中移除 .workbuddy/（AI 助手内部数据泄漏修复）

### 文档
- 新增 ARCHITECTURE.md（架构全景文档）
- 新增 DEVELOPMENT.md（开发指南）
- README.md 重写为专业项目首页

---

## [0.1.1] — 2026-05-08

### 修复
- 修复 test_regression.py 中引用已删除模块 `docx_self_check` 的 bug（S1）
- 统一全部版本号为 0.1.1，清除 v3.6 遗留（S2）
- check_docx() 文件不存在时优雅降级而非抛异常
- 修正 pyproject.toml 中 pytest 最低版本声明

---

## [0.1.0] — 2026-05-08

### 新增
- Git 仓库初始化、.gitignore、README.md（P0-1）
- src-layout 标准项目目录结构（P0-2）
- pyproject.toml 项目元数据与依赖声明（P0-3）
- 将 806 行单文件脚本拆分为 14 个模块（P0-4）
- 外部化配置：7 个 JSON 文件（P0-5）
- GitHub 远程仓库推送

---

## [3.6] — 2026-04-23 (v3.6 单文件脚本，GEHD 项目前身)

### 核心能力
- 5 层规则引擎：L1 白名单 → L2 黑名单 → L2.5 非实体检测 → L3 启发式评分 → L4 核查队列
- L2.5 非实体幻觉检测（统计/引述/时间线）
- L3.6 内部一致性检查（多出现/金额矛盾）
- L4 JSON 标准化验证队列输出
- 18 个 pytest 回归测试
