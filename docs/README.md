# GEHD 文档索引

## 核心文档

| 文件 | 内容 | 适合 |
|------|------|------|
| [architecture.md](./architecture.md) | 架构全景：五层引擎数据流、模块依赖、配置系统、评分维度 | 了解项目结构 |
| [development.md](./development.md) | 开发指南：环境搭建、运行测试、代码规范、修改场景、技术债务 | 开始写代码 |
| [ai-guide.md](./ai-guide.md) | 开发者参考手册：管道调用、审计模式、模式选择 | AI 助手操作 GEHD |
| [COLLABORATION.md](./COLLABORATION.md) | 多智能体协作协议：六方协作结构、文件域划分、Git 工作流、冲突处理 | 参与协作 |
| [plan.md](./plan.md) | 开发路线图：已实现、v0.6.0 计划、v0.7.0 愿景 | 了解规划 |

## 设计文档

| 文件 | 内容 |
|------|------|
| [designs/interfaces/p2-2-interface.md](./designs/interfaces/p2-2-interface.md) | P2-2 适配层接口设计（冻结）：DocumentText 数据结构、引擎入口、输出承诺 |
| [designs/architecture/v0.4-roadmap.md](./designs/architecture/v0.4-roadmap.md) | v0.4.0 历史路线图归档 |
| [designs/architecture/pipeline-v0.5.0.md](./designs/architecture/pipeline-v0.5.0.md) | 管道架构设计决策归档 |
| [designs/agents/ci-role-design.md](./designs/agents/ci-role-design.md) | CI（合规审查）角色设计案（暂不激活） |

## 项目根目录文档

| 文件 | 内容 |
|------|------|
| [../README.md](../README.md) | 项目首页（快速开始、核心能力） |
| [../CHANGELOG.md](../CHANGELOG.md) | 版本变更记录 |

## 推荐阅读顺序

1. [README.md](../README.md) — 了解项目是干什么的
2. [architecture.md](./architecture.md) — 理解代码怎么组织的
3. [development.md](./development.md) — 学会怎么搭环境、跑测试、改代码
4. [ai-guide.md](./ai-guide.md) — AI 如何操作 GEHD 完成自迭代
5. [COLLABORATION.md](./COLLABORATION.md) — 多智能体如何协作开发
6. [designs/interfaces/p2-2-interface.md](./designs/interfaces/p2-2-interface.md) — 引擎接口契约（U 开发参考）
