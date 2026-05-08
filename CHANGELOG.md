# 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) (SemVer 2.0)。

## [0.2.0] — 2026-05-09

### Iteration 2 完成 — 工程化提升

- **P1-0**: GEHDConfig dataclass 重构 — 30+全局变量→单一配置数据类，删除 _apply_external_config 等 90 行机械代码
- **P1-1**: 全量类型注解 — mypy 22 文件零错误，TYPE_CHECKING 模式导入 Document 类型
- **P1-2**: Ruff 格式化 + lint — 16 文件格式化，25 lint→0，新增 .editorconfig
- **P1-3**: logging 文件日志 — gehd.log 含时间戳和结构化消息，终端输出保持 print()（测试兼容）
- **P1-4**: 异常处理标准化 — except Exception→精确类型（ValueError/OSError/JSONDecodeError）
- **P1-5**: 单元测试 — 27 新测试，总测试 45，覆盖率 30%→85%

### 质量指标
- 测试: **45/45** (27 单元 + 18 回归)
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
