# U 组工作区

GEHD UI 开发组（U）的过程文件存储区。仅本地保留，不推 GitHub。

## 目录约定

| 目录 | 用途 | 命名规范 |
|------|------|------|
| `mockups/` | GUI 截图、界面参考 | `YYYY-MM-DD_描述.png` |
| `iterations/` | 迭代计划、功能清单、技术笔记 | `iter-N_描述.md` |

## 当前状态

- GUI v1 已交付（P1/P2 功能完整，17 测试全绿，mypy 零错误，ruff 零错误）
- QA 审计已闭合，P2 覆盖率延迟至 v0.3.0（PM 已确认）
- 等待 E 组 P2-3/P2-4 推进以触发新 UI 需求

## 相关文件

- 代码：`src/hallucination_checker/gui/`
- 测试：`tests/test_gui.py`
- 接口契约：`docs/p2-2-interface.md`
- 协作协议：`docs/COLLABORATION.md`
