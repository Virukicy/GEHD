"""
GEHD — 泛化实体幻觉检测 (Generalized Entity Hallucination Detection)

基于多源交叉校验的轻量级文档幻觉核查工具。
采用纯规则引擎（非 LLM 自查），可审计、可解释、可扩展。

架构：5 层规则引擎
  L1 白名单放行 → L2 黑名单拦截 → L2.5 非实体检测
  → L3 启发式评分 → L3.6 内部一致性 → L4 联网核查队列
"""

__version__ = "0.1.2"
__all__ = ["engine", "io", "cli", "gui"]
