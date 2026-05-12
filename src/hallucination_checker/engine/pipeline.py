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

    v0.4.0-beta 阶段:
      - 规则管道 (L1→L4) 与 v0.3.0 完全等价
      - llm_pre 开关激活时，LLM 前置过滤候选实体
    """

    from .checker import _gehd_check_impl

    # 加载管道配置
    pipeline_cfg = _load_pipeline_config()

    all_parts = [(p.location, p.text) for p in text.parts]
    issues, warnings, stats, l4_queue = _gehd_check_impl(
        all_parts, text.full_text, config, output_verify_queue,
    )

    context = PipelineContext(
        issues=issues,
        warnings=warnings,
        stats=stats,
        l4_queue=l4_queue,
        candidates=l4_queue if l4_queue else [],  # v0.4.0-rc: 候选来自 L4 队列
        decision_log=[],
    )

    # LLM 前置过滤（v0.4.0-beta）
    if pipeline_cfg.get('llm_pre', False) and llm is not None:
        from .llm.pre_filter import llm_pre_filter
        context = llm_pre_filter(context, llm, config)

    # LLM 后置语义验证（v0.4.0-rc）
    if pipeline_cfg.get('llm_post', False) and llm is not None:
        from .llm.post_filter import llm_post_filter
        context = llm_post_filter(context, llm, config)

    return context


def _load_pipeline_config() -> dict:
    """加载 config/pipeline.json 的 steps 节。"""
    from .config import _find_config_dir
    cfg_dir = _find_config_dir()
    if cfg_dir is None:
        return {}
    path = cfg_dir / 'pipeline.json'
    try:
        import json
        with open(path, encoding='utf-8') as f:
            data: dict = json.load(f)
        return data.get('steps', {})
    except (OSError, json.JSONDecodeError):
        return {}
