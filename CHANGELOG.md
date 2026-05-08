# 更新日志

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/) (SemVer 2.0)。

## [0.1.0] — 开发中

### 新增
- Git 仓库初始化、.gitignore、README.md (P0-1)
- src-layout 标准项目目录结构 (P0-2)

---

## [3.6] — 2026-04-23 (v3.6 单文件脚本，GEHD 项目前身)

### 核心能力
- 5 层规则引擎：L1 白名单 → L2 黑名单 → L2.5 非实体检测 → L3 启发式评分 → L4 核查队列
- L2.5 非实体幻觉检测（统计/引述/时间线）
- L3.6 内部一致性检查（多出现/金额矛盾）
- L4 JSON 标准化验证队列输出
- 18 个 pytest 回归测试
