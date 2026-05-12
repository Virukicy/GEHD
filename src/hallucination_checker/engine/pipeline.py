"""
管道编排器 —— v0.5.0 注册表驱动多路径调度。

路径:
  full:    rules → cross_validate → llm_pre → web_verify → llm_post → output_queue
  fast:    rules → cross_validate → llm_pre → llm_direct_verify → output_queue
  offline: rules → output_queue  (等价 v0.3.0 纯规则)
"""

from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from ..io.document_text import DocumentText
    from .config import GEHDConfig
    from .llm.adapter import LLMAdapter


# ---- 契约定义 ----

STAGE_CONTRACTS: dict[str, dict] = {
    'cross_validate': {
        'requires': ['l4_queue'],
        'produces': ['decision_log'],
    },
    'llm_pre': {
        'requires': ['candidates'],
        'produces': ['candidates', 'decision_log'],
    },
    'web_verify': {
        'requires': ['l4_queue'],
        'produces': ['l4_queue'],
    },
    'llm_post': {
        'requires': ['l4_queue'],
        'produces': ['decision_log'],
    },
    'llm_direct_verify': {
        'requires': ['candidates'],
        'produces': ['decision_log'],
    },
}

ADAPTER_CONTRACTS: dict[str, dict] = {
    'llm': {
        'requires_config': ['llm.json.model', 'secrets.json.llm_api_key'],
    },
}

# ---- 三路径阶段注册表 ----

STAGES: dict[str, list[str]] = {
    'full':    ['rules', 'cross_validate', 'llm_pre', 'web_verify', 'llm_post', 'output_queue'],
    'fast':    ['rules', 'cross_validate', 'llm_pre', 'llm_direct_verify', 'output_queue'],
    'offline': ['rules', 'output_queue'],
}


# ---- PipelineContext ----

class PipelineContext(TypedDict, total=False):
    """管道上下文 —— 跨阶段共享状态。"""
    issues: list[str]
    warnings: list[str]
    stats: dict
    l4_queue: list[dict]
    candidates: list[dict]
    decision_log: list[dict]
    status: dict  # v0.5.0: 阶段执行状态


# ---- 主入口 ----

def run_pipeline(
    text: DocumentText,
    config: GEHDConfig,
    llm: LLMAdapter | None = None,
    output_verify_queue: bool = False,
    progress_callback=None,
) -> PipelineContext:
    """v0.5.0 注册表驱动多路径管道。

    mode 取自 config/pipeline.json → mode 字段。
    """
    # 1. 加载配置
    pipeline_cfg = _load_pipeline_config()
    mode = pipeline_cfg.get('mode', 'full')
    stages = STAGES.get(mode, STAGES['full'])

    # 2. 验证适配器契约
    _validate_adapter_contracts(pipeline_cfg)

    # 3. 运行规则引擎（唯一必开阶段）
    all_parts = [(p.location, p.text) for p in text.parts]
    result = _run_rules(all_parts, text.full_text, config, output_verify_queue)

    # 4. 初始化 PipelineContext
    context = PipelineContext(
        issues=result['issues'],
        warnings=result['warnings'],
        stats=result['stats'],
        l4_queue=result['l4_queue'],
        candidates=result['candidates'],
        decision_log=[],
        status={},
    )

    # 5. 按注册表顺序执行各阶段
    for stage_name in stages:
        if stage_name in ('rules', 'output_queue'):
            continue
        if progress_callback:
            progress_callback(stage_name)
        context = _validate_and_run_stage(stage_name, context, llm, config)

    # 6. 生成验证队列
    if output_verify_queue and 'output_queue' in stages:
        _write_l4_queue(context)

    return context


def _run_rules(
    all_parts: list, full_text: str, config: GEHDConfig, output_verify_queue: bool,
) -> dict:
    """运行规则引擎，返回解包为 dict。"""
    from .checker import _gehd_check_impl
    issues, warnings, stats, l4_queue, l3_ranked = _gehd_check_impl(
        all_parts, full_text, config, output_verify_queue,
    )
    l3_candidates = [
        {'word': c['word'], 'score': c.get('score', 0), 'category': c.get('category', '')}
        for c in l3_ranked
    ]
    return {
        'issues': issues,
        'warnings': warnings,
        'stats': stats,
        'l4_queue': l4_queue,
        'candidates': l3_candidates,
    }


# ---- 适配器契约验证 ----

def _validate_adapter_contracts(pipeline_cfg: dict) -> None:
    """管道启动时验证所有需要的适配器配置齐全。

    仅验证模式注册表中存在且 steps 中开启的阶段。
    """
    mode = pipeline_cfg.get('mode', 'full')
    enabled_in_mode = set(STAGES.get(mode, []))
    steps = pipeline_cfg.get('steps', {})

    llm_stages = {'llm_pre', 'llm_post', 'llm_direct_verify'}
    # 仅验证 mode 中包含且 steps 中为 true 的 LLM 阶段
    active_llm = enabled_in_mode & llm_stages
    active_llm = {s for s in active_llm if steps.get(s, False)}

    if not active_llm:
        return  # 无 LLM 阶段激活 → 跳过

    contract = ADAPTER_CONTRACTS['llm']
    for key in contract['requires_config']:
        value = _resolve_config_path(key)
        if not value:
            raise ValueError(
                f'[GEHD pipeline] LLM 阶段 {sorted(active_llm)} 已启用，'
                f'但配置项 "{key}" 缺失或为空。'
                f'请检查 config/ 目录下的对应 JSON 文件。'
            )


def _resolve_config_path(path: str) -> str:
    """解析 config.json 路径，如 'secrets.json.llm_api_key' → 对应值。"""
    import json

    from .config import _find_config_dir

    cfg_dir = _find_config_dir()
    if cfg_dir is None:
        return ''

    parts = path.split('.')
    filename = parts[0]
    keys = parts[1:]

    try:
        with open(cfg_dir / filename, encoding='utf-8') as f:
            data: dict = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ''

    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, '')
        else:
            return ''
    return str(data) if data else ''


# ---- 契约式阶段执行 ----

def _validate_and_run_stage(
    stage_name: str,
    context: PipelineContext,
    llm: LLMAdapter | None = None,
    config: GEHDConfig | None = None,
) -> PipelineContext:
    """验证阶段输入 → 执行 → 记录输出。"""
    contract = STAGE_CONTRACTS.get(stage_name)
    if contract is None:
        return context  # rules/output_queue 无契约

    # 验证 requires
    for field in contract['requires']:
        value = context.get(field)
        if value is None or (isinstance(value, list) and len(value) == 0):
            context.setdefault('decision_log', []).append({
                'stage': stage_name,
                'status': 'skipped',
                'reason': f'required field "{field}" is missing or empty',
                'timestamp': datetime.datetime.now().isoformat(),
            })
            context.setdefault('status', {})[stage_name] = 'skipped'
            return context

    # 执行阶段
    context = _dispatch_stage(stage_name, context, llm, config)

    # 验证 produces
    for field in contract['produces']:
        if field not in context:
            context.setdefault('decision_log', []).append({
                'stage': stage_name,
                'status': 'warning',
                'reason': f'expected output field "{field}" not produced',
                'timestamp': datetime.datetime.now().isoformat(),
            })

    return context


# ---- 阶段分发 ----

def _dispatch_stage(
    stage_name: str,
    context: PipelineContext,
    llm: LLMAdapter | None = None,
    config: GEHDConfig | None = None,
) -> PipelineContext:
    """根据阶段名调用具体阶段函数。"""
    if stage_name == 'cross_validate':
        # v0.5.0: cross_validate 需要 DocumentText 上下文，管道调度暂存 decision_log
        context.setdefault('decision_log', []).append({
            'stage': 'cross_validate',
            'status': 'deferred',
            'reason': 'cross_validate 需 GUI/CLI 独立触发',
            'timestamp': datetime.datetime.now().isoformat(),
        })

    elif stage_name == 'llm_pre':
        if llm is None:
            return context
        from .llm.pre_filter import llm_pre_filter
        context = llm_pre_filter(context, llm, config)

    elif stage_name == 'web_verify':
        context = _run_web_verify(context, config)

    elif stage_name == 'llm_post':
        if llm is None:
            return context
        from .llm.post_filter import llm_post_filter
        context = llm_post_filter(context, llm, config)

    elif stage_name == 'llm_direct_verify':
        if llm is None:
            return context
        from .llm.direct_verify import llm_direct_verify
        context = llm_direct_verify(context, llm, config)

    return context


# ---- web_verify 适配 (含 feedback 逻辑) ----

def _run_web_verify(context: PipelineContext, config: GEHDConfig) -> PipelineContext:
    """运行 L4 联网核查 + 判决反写。"""
    from .layers.l4_web_verify import get_verification_summary, verify_queue

    l4_queue = context.get('l4_queue', [])
    if not l4_queue:
        return context

    l4_queue = verify_queue(l4_queue, config)
    summary = get_verification_summary(l4_queue)
    stats = context.get('stats', {})
    stats['l4_verified_real'] = summary['verified_real']
    stats['l4_verified_fake'] = summary['verified_fake']
    stats['l4_queue_size'] = len(l4_queue)

    # L4 判决反写：verified_fake → 升级 issues, verified_real → 降级 warnings
    issues = list(context.get('issues', []))
    warnings = list(context.get('warnings', []))
    for entry in l4_queue:
        if entry.get('status') == 'verified_fake':
            word = entry.get('word', '未知')
            issues.append(
                f'[L4 核实] 实体"{word}"联网核查判定为虚构，建议核实'
            )
        elif entry.get('status') == 'verified_real':
            word = entry.get('word', '未知')
            warnings.append(
                f'[L4 核实] 实体"{word}"联网核查判定为真实，原声明可信'
            )

    context['issues'] = issues
    context['warnings'] = warnings
    context['stats'] = stats
    context['l4_queue'] = l4_queue
    return context


# ---- 配置文件加载 ----

def _load_pipeline_config() -> dict:
    """加载 config/pipeline.json 全量。"""
    import json

    from .config import _find_config_dir

    cfg_dir = _find_config_dir()
    if cfg_dir is None:
        return {}
    path = cfg_dir / 'pipeline.json'
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_l4_queue(context: PipelineContext) -> None:
    """输出 L4 验证队列到 workspace/。"""
    import json
    from pathlib import Path

    l4_queue = context.get('l4_queue', [])
    if not l4_queue:
        return

    workspace = Path(__file__).resolve().parents[3] / 'workspace'
    workspace.mkdir(parents=True, exist_ok=True)
    output = workspace / 'l4_queue.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(l4_queue, f, ensure_ascii=False, indent=2)
