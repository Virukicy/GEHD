"""
管道编排器 —— 组合规则引擎 + 交叉校验 + LLM + 联网核查。

v0.4.0-alpha: 规则管道完全等价于 v0.3.0 gehd_check()。
LLM 适配器预留接口，实际调用留待 v0.5.0。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from ..io.document_text import DocumentText
    from .config import GEHDConfig
    from .llm.adapter import LLMAdapter


class PipelineContext(TypedDict, total=False):
    """管道上下文 —— 跨阶段共享状态。"""
    issues: list[str]
    warnings: list[str]
    stats: dict
    l4_queue: list[dict]
    candidates: list[dict]
    decision_log: list[dict]


def run_pipeline(
    text: DocumentText,
    config: GEHDConfig,
    llm: LLMAdapter | None = None,
    output_verify_queue: bool = True,
) -> PipelineContext:
    """运行全链路核查管道。

    v0.4.0-alpha 阶段:
      - 规则管道 (L1→L4) 与 v0.3.0 完全等价
      - llm 参数预留，此版本忽略
    """
    from .checker import gehd_check

    issues, warnings, stats, l4_queue = gehd_check(
        text, config, output_verify_queue=output_verify_queue,
    )

    return PipelineContext(
        issues=issues,
        warnings=warnings,
        stats=stats,
        l4_queue=l4_queue,
        candidates=[],  # v0.5.0 populate
        decision_log=[],  # v0.5.0 populate
    )
