"""
GEHD 全局配置 —— dataclass 封装，替代模块级全局变量。

P1-0 重构：
  - GEHDConfig dataclass：所有配置的单一真实来源
  - GEHDConfig.default()：内置默认值
  - GEHDConfig.from_json_dir()：从 config/*.json 加载外部化配置
  - load_config()：自动检测并加载（JSON 优先，回退默认值）

使用：
  config = load_config()
  engine.gehd_check(doc, config=config)
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass, field
from pathlib import Path

# ============================================================
# 版本信息（模块级，不属于配置数据）
# ============================================================
GEHD_VERSION = '0.3.0-beta'
GEHD_VERSION_DATE = '2026-05-09'
GEHD_VERSION_HASH = 'v030alpha-p21-p22'

# ============================================================
# L4 协议枚举（模块级常量，永不变化）
# ============================================================
L4_STATUS_PENDING = 'pending_verification'
L4_VERDICT_REAL = 'verified_real'
L4_VERDICT_FAKE = 'verified_fake'
L4_VERDICT_MANUAL = 'need_manual_check'
L4_VERDICT_UNABLE = 'unable_to_verify'
L4_QUEUE_SUFFIX = '_l4_queue.json'
L4_CACHE_SUFFIX = '_l4_cache.json'


# ============================================================
# GEHDConfig dataclass
# ============================================================


@dataclass(frozen=True)
class GEHDConfig:
    """GEHD 引擎的完整配置。

    设计原则（见 docs/development.md §五）：
      - config/*.json 是配置的唯一真实来源
      - GUI/CLI/AI 共享同一个 GEHDConfig 实例
      - 不可变（frozen=True）：创建后无法修改，避免意外副作用
    """

    # --- 评分阈值 ---
    score_high_threshold: int = 65
    score_medium_threshold: int = 45
    score_minimum: int = 10
    score_adjective_penalty: int = 30
    score_l35_penalty: int = 30
    score_single_char_platform: int = 15
    score_high_freq_bonus: int = 10
    score_med_freq_bonus: int = 3
    score_plausible_char_penalty: int = -10

    # --- 文本处理参数 ---
    max_consecutive_blank_paragraphs: int = 3
    long_text_threshold_chars: int = 300
    context_window_chars: int = 10
    min_candidate_length: int = 2
    deep_search_threshold: int = 55
    l4_search_timeout: float = 5.0
    l4_auto_verify: bool = False  # 是否在扫描时自动执行联网核查

    # --- L1 白名单 ---
    whitelist: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                '淘宝',
                '天猫',
                '京东',
                '拼多多',
                'PDD',
                'TB',
                '抖音',
                '小红书',
                '闲鱼',
                '苏宁',
                '国美',
                '美团',
                '美团龙珠',
                '饿了么',
                '滴滴',
                '支付宝',
                '微信支付',
                '微信',
                'Apple',
                '苹果',
                '华为',
                '小米',
                'OPPO',
                'vivo',
                '微软',
                '谷歌',
                'Google',
                '百度',
                '阿里',
                '阿里巴巴',
                '腾讯',
                '字节跳动',
                '网易',
                '携程',
                '去哪儿',
                '58同城',
                'OpenAI',
                'Anthropic',
                'Meta',
                'Facebook',
                'Amazon',
                'DeepMind',
                'NVIDIA',
                '英伟达',
                'AMD',
                'Intel',
                '英特尔',
                '五菱宏光',
                '五菱',
                '长安',
                '长城',
                '吉利',
                '比亚迪',
                '丰田',
                '本田',
                '大众',
                '奔驰',
                '宝马',
                '奥迪',
                '特斯拉',
                'Tesla',
                '蔚来',
                '理想',
                '小鹏',
                '智元机器人',
                '智元',
                '它石智航',
                '龙旗科技',
                '宇树科技',
                '傅利叶智能',
                '银河通用',
                '商汤',
                '旷视',
                '云从科技',
                '依图',
                '月之暗面',
                'MiniMax',
                '智谱AI',
                '百川智能',
                '零一万物',
                '阶跃星辰',
                '深度求索',
                'DeepSeek',
                'Kimi',
                '通义千问',
                '文心一言',
                '豆包',
                '科大讯飞',
                'iFLYTEK',
                '讯飞',
                '36氪',
                '钛媒体',
                '投资界',
                'PitchBook',
                '高瓴创投',
                '高瓴',
                '红杉中国',
                '红杉资本',
                '红杉',
                '启明创投',
                '线性资本',
                '蓝驰创投',
                '中金资本',
                'IDG资本',
                '经纬中国',
                '真格基金',
                '斯坦福大学',
                '斯坦福',
                '麻省理工',
                'MIT',
                '哈佛大学',
                '清华大学',
                '北京大学',
                '浙江大学',
                '复旦大学',
                '上海交通大学',
                '中国科学技术大学',
                '中科大',
                '南京大学',
                '武汉大学',
                '中山大学',
                '华中科技大学',
                '西安交通大学',
                '同济大学',
                '南开大学',
                '天津大学',
                '山东大学',
                '四川大学',
                '电子科技大学',
                '成电',
                '北京航空航天大学',
                '北航',
                '北京理工大学',
                '北理工',
                '北京师范大学',
                '北师大',
                '中国人民大学',
                '人大',
                '上海财经大学',
                '上财',
                '中国地质大学',
                '地质大学',
                '地大',
                '悉尼大学',
                'USYD',
                '悉尼',
                '国家网信办',
                '网信办',
                '工信部',
                '发改委',
                '教育部',
                '中国科学院',
                '中科院',
                '中国工程院',
                '世界卫生组织',
                'WHO',
                'ISO',
                'IEEE',
                'ACM',
                '联合国',
                '欧盟',
                '央视网',
                '央视',
                'CCTV',
                '世界互联网大会',
                '未来萤火虫',
                'python-docx',
                'Python',
                'JavaScript',
                'Node.js',
                'Windows',
                'macOS',
                'Linux',
                'iOS',
                'Android',
                '中国',
                '北京',
                '上海',
                '广州',
                '深圳',
                '杭州',
                '南昌',
                '香港',
                '绵阳',
                '无锡',
                '南京',
            }
        )
    )

    # --- L2 黑名单 ---
    blacklist: tuple[str, ...] = field(
        default_factory=lambda: (
            '母丑',
            '母丑购',
            '母丑京东',
            '母丑商城',
        )
    )

    # --- L3 实体提取正则 ---
    entity_patterns: tuple[tuple[str, str, int], ...] = field(
        default_factory=lambda: (
            (
                r'([\u4e00-\u9fff]{1,3}(?:购|商城|超市|百货|优选|特卖|专营|官方店|旗舰店))',
                '电商平台名',
                60,
            ),
            (
                r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,6}(?:公司|集团|企业|科技|股份|有限|控股|投资|基金|银行|保险|证券|信托))',
                '公司机构名',
                50,
            ),
            (
                r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,5}(?:大学|学院|学校|研究院|研究所|实验室|医院|中心|协会|学会|组织))',
                '学术机构名',
                45,
            ),
            (r'\b([\u4e00-\u9fff]{2,5}(?:牌|系列|型号|版))\b', '产品品牌名', 40),
            (
                r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,6}(?:局|委员会|办公厅|管理处|监管局|指挥部|办公室))',
                '政府机构名',
                48,
            ),
            (
                r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{3,8}(?:行业协会|联合会|促进会|联盟|商会|公会))',
                '行业组织名',
                45,
            ),
            (
                r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,6}(?:微电子|半导体|集成电路|光电子))',
                '半导体企业名',
                50,
            ),
            (r'([A-Z][A-Za-z0-9]*[-–][A-Z0-9][A-Za-z0-9]*)', '产品型号', 42),
            (
                r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,3})(?:先生|女士|小姐|博士|教授|老师|工程师|经理|总监|总|董)',
                '人名+称谓',
                35,
            ),
            (
                r'(?:^|[^\u4e00-\u9fff]|位于|在|于|至|往|从|的)([\u4e00-\u9fff]{2,4}(?:省|市|县|区|镇|乡|村|路|街|道|广场|大厦|写字楼|商场|机场|车站|港口))',
                '地名',
                30,
            ),
            (
                r'["\u300c\u300d\u201c\u201d]([\u4e00-\u9fff]{2,10})(?:计划|行动|工程|倡议|战略|峰会|论坛|大会|博览会)["\u300c\u300d\u201c\u201d]',
                '会议/IP名',
                32,
            ),
            (
                r'["\u300c\u300d\u201c\u201d]([\u4e00-\u9fff]{2,8})["\u300c\u300d\u201c\u201d]',
                '引用名称/IP名',
                25,
            ),
            (
                r'\b([A-Z][a-z]{2,}(?:[ -][A-Z][a-z]{2,}){1,2})(?: Inc| Corp| LLC| Ltd| Co| Group)?\b',
                '英文机构/品牌名',
                40,
            ),
        )
    )

    # --- L2.5 非实体检测正则 ---
    l25_patterns: tuple[tuple[str, str, int], ...] = field(
        default_factory=lambda: (
            (r'(\d+(?:\.\d+)?(?:万亿|亿|万)?(?:元|美元|人民币|欧元))', '可疑统计金额', 48),
            (
                r'(?:增长率?|增速|增幅|涨幅|同比|环比|市占率?|占有率|渗透率|转化率|复购率)[超达]?\s*(\d+(?:\.\d+)?%)',
                '可疑百分比数据',
                45,
            ),
            (
                r'(?<!已)(?<!完成)(?:达|约|将近|超过|突破)\s*(\d+(?:\.\d+)?(?:万亿|亿|万)?\s*(?:元|美元|人|户|家|台|套))',
                '可疑规模描述',
                42,
            ),
            (
                r'据\s*([\u4e00-\u9fff]{2,4}(?:教授|博士|院士|CEO|总裁|总[经理裁]|部长|司长|局长|主任|所长))\s*(?:称|表示|透露|指出|强调|透露|宣布)',
                '权威引述',
                50,
            ),
            (
                r'["\u201c]((?:(?:[\u4e00-\u9fff]{1,3}(?:教授|博士|院士|CEO|总裁|总[经理裁]|部长|司长|局长|主任|所长|先生|女士))'
                r'|(?:[\u4e00-\u9fff]{2,6}(?:公司|集团|研究院|研究所|大学|学院|银行|部委|协会|学会))'
                r'|(?:\d+(?:\.\d+)?(?:%|(?:万亿|亿|万)?(?:元|美元|人|家)))'
                r'|(?:20\d{2}年|[一二三四]季度|Q[1-4]|[上下本]月|今年|去年|前年)'
                r').{0,50}[^"\u201d]{5,})["\u201d]',
                '直接引语(待核实)',
                35,
            ),
            (
                r'(?:于|在|预计|将于|将在|计划于)\s*(20\d{2}年(?:[一二三四]?季度|Q[1-4]|[1-12]月))',
                '时间线引用',
                38,
            ),
            (
                r'(?:已于?|已在|已经完成|已完成|成功实现)\s*(20\d{2}(?:年[1-12]月|[/-]\d{1,2}))',
                '完成时间声明',
                40,
            ),
        )
    )

    # --- L2.5 排除短语 ---
    l25_exclude_phrases: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                'GDP',
                'CPI',
                'PMI',
                'GDP增长率',
                '2026年',
                '2025年',
                '2024年',
                '2023年',
            }
        )
    )

    # --- 噪音前缀 ---
    noise_prefixes: tuple[str, ...] = field(
        default_factory=lambda: (
            '在',
            '的',
            '是',
            '有',
            '被',
            '从',
            '向',
            '对',
            '为',
            '由',
            '把',
            '与',
            '和',
            '及',
            '或',
            '而',
            '但',
            '若',
            '如',
            '因',
        )
    )

    # --- 排除词 ---
    entity_suffixes_for_exclusion: tuple[str, ...] = field(
        default_factory=lambda: (
            '中心',
            '公司',
            '集团',
            '研究院',
            '研究所',
            '实验室',
            '协会',
            '学会',
            '管理局',
            '委员会',
            '办公室',
        )
    )

    exclude_words: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                '采购',
                '采购完毕',
                '采购日',
                '采购建议',
                '购置',
                '购买',
                '弹力网',
                '电网',
                '水电网',
                '断网',
                '力网',
                '上网',
                '在电商平台',
                '购物平台',
                '电商平台',
                '交易平台',
                '销售平台',
                '服务平台',
                '共享平台',
                '云平台',
                '技术平台',
                '数据平台',
                '购物中心',
                '大型商场',
                '综合百货',
                '快乐购',
                '快乐购的',
                '正在购',
                '这意味着企业',
                '已经走出了实验室',
                '和规模效应的公司',
                '获投企业',
                '科大等高校及企业',
                '京东全链路',
                '备中国地质大学',
                '权威科技',
                '领先科技',
                '知名科技',
                '大型科技',
                '专业科技',
                '顶级科技',
                '大型企业',
                '车规级芯片',
                '训练芯片',
                '推理芯片',
                'AI芯片',
                '算力芯片',
                '智能学院',
                '机构的战略投资',
                '用层仍有大量投资',
                '硅谷初创企业',
                '包括多家上市公司',
                '学院联合多家企业',
                'Test Suite',
                'Robotics',
                'Machine Intelligence',
                'Suite',
                'Machine',
                '子人工智能实验室',
                '身智能联合实验室',
                '关村的灵境研究院',
                '年国内',
                '据财新报道',
                '技术路',
                '公开报道',
            }
        )
    )

    # --- 形容词前缀 ---
    adjective_prefixes: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                '权威',
                '领先',
                '知名',
                '大型',
                '专业',
                '顶级',
                '头部',
                '新兴',
                '热门',
                '主流',
                '重要',
                '核心',
                '关键',
                '主要',
                '多家',
                '众多',
                '部分',
                '相关',
                '其他',
                '上述',
                '某些',
            }
        )
    )

    # --- L3.7 声明提取模式 ---
    declaration_patterns: tuple[tuple[str, str, int], ...] = field(
        default_factory=lambda: (
            (
                r'([\u4e00-\u9fff]{2,8}(?:与|和|同|联合|携手|合作)'
                r'[\u4e00-\u9fff]{2,8}(?:联合|共同|合作|携手|正式|宣布|签署|达成)'
                r'(?:成立|建立|设立|创建|组建|推出|启动|开展|发布))',
                '合作关系声明',
                68,
            ),
            (
                r'([\u4e00-\u9fff]{2,5}(?:教授|博士|院士|CEO|总裁|创始人|先生|女士|经理|总))'
                r'.{0,20}(?:宣布|称|表示|透露|强调|指出|认为|声称)',
                '权威人物声明',
                68,
            ),
            (
                r'(?:[\u4e00-\u9fff]{2,4}(?:教授|博士))在'
                r'(?:[\u4e00-\u9fff]{2,8}|[A-Z][a-z]+)上(?:发表|刊发|发布)',
                '学术成果声明',
                68,
            ),
            (
                r'(?:据|根据|参考|援引)'
                r'(?:[\u4e00-\u9fff]{2,8}(?:日报|周报|时报|杂志|通讯社|新闻|网|报))',
                '媒体引述声明',
                48,
            ),
            (
                r'([\u4e00-\u9fff]{2,6}(?:部|委|局|办|署|院|会))'
                r'(?:发布|印发|出台|颁布|实施)',
                '政策文件声明',
                48,
            ),
            (
                r'(?:[\u4e00-\u9fff]{2,6}(?:宣布|称|表示|透露|强调|指出))'
                r'(?:了|过|到|在|将|会|已|正)',
                '组织声明',
                45,
            ),
        )
    )

    # --- 单字平台后缀（电商场景配置，用于 L3 评分） ---
    single_char_platform_suffixes: frozenset[str] = field(
        default_factory=lambda: frozenset({'购', '宝', '东'})
    )

    # --- 可信字符列表（电商场景配置，用于 L3 评分降分） ---
    plausible_chars: frozenset[str] = field(
        default_factory=lambda: frozenset({
            '淘', '京', '拼', '多', '美', '苏', '阿', '腾', '百',
        })
    )

    # --- 可信字符生效类别 ---
    plausible_char_categories: frozenset[str] = field(
        default_factory=lambda: frozenset({'电商平台名', '公司机构名'})
    )

    # ---- 工厂方法 ----

    @classmethod
    def default(cls) -> GEHDConfig:
        """返回内置默认配置。"""
        return cls()

    @classmethod
    def from_json_dir(cls, config_dir: Path) -> GEHDConfig:
        """从 config/ 目录加载配置，JSON 值覆盖默认值。

        JSON 文件缺失或格式错误时静默回退到默认值。
        未知阈值键触发 UserWarning。
        """
        kwargs: dict = {}

        # --- 白名单 ---
        wl_items = _load_list(config_dir / 'whitelist.json', 'whitelist')
        if wl_items is not None:
            kwargs['whitelist'] = frozenset(wl_items)

        # --- 黑名单 ---
        bl_items = _load_list(config_dir / 'blacklist.json', 'blacklist')
        if bl_items is not None:
            kwargs['blacklist'] = tuple(bl_items)

        # --- 实体提取模式 ---
        ep_items = _load_patterns(config_dir / 'entity_patterns.json', 'patterns')
        if ep_items is not None:
            kwargs['entity_patterns'] = tuple(ep_items)

        # --- L2.5 模式 ---
        l25_items = _load_patterns(config_dir / 'l25_patterns.json', 'patterns')
        if l25_items is not None:
            kwargs['l25_patterns'] = tuple(l25_items)

        # --- 声明提取模式 ---
        decl_items = _load_patterns(
            config_dir / 'declaration_patterns.json', 'patterns'
        )
        if decl_items is not None:
            kwargs['declaration_patterns'] = tuple(decl_items)

        # --- 排除词 ---
        ex_items = _load_list(config_dir / 'exclude_words.json', 'exclude_words')
        if ex_items is not None:
            kwargs['exclude_words'] = frozenset(ex_items)

        # --- 形容词前缀 ---
        adj_items = _load_list(config_dir / 'adjective_prefixes.json', 'adjective_prefixes')
        if adj_items is not None:
            kwargs['adjective_prefixes'] = frozenset(adj_items)

        # --- 评分阈值 ---
        thresholds = _load_thresholds(config_dir / 'thresholds.json')
        if thresholds is not None:
            kwargs.update(thresholds)

        return cls(**kwargs)


# ---- JSON 加载辅助函数 ----


def _load_list(filepath: Path, key: str) -> list[str] | None:
    """从 JSON 文件中加载字符串列表。"""
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        items = data.get(key, [])
        if isinstance(items, list) and len(items) > 0:
            return items
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def _load_patterns(filepath: Path, key: str) -> list[tuple[str, str, int]] | None:
    """从 JSON 文件中加载 (pattern, category, score) 元组列表。"""
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)
        items = data.get(key, [])
        if isinstance(items, list) and len(items) > 0:
            return [
                (item['pattern'], item['category'], item['base_score'])
                for item in items
                if all(k in item for k in ('pattern', 'category', 'base_score'))
            ]
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def _load_thresholds(filepath: Path) -> dict | None:
    """从 thresholds.json 加载阈值，映射到 dataclass 字段名。"""
    try:
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)

        scores = data.get('scores', {})
        text = data.get('text_processing', {})
        l4 = data.get('l4', {})
        flat: dict[str, int] = {**scores, **text, **l4}

        result: dict = {}
        # JSON 键名 → dataclass 字段名映射
        _key_map = {
            'high_threshold': 'score_high_threshold',
            'medium_threshold': 'score_medium_threshold',
            'minimum': 'score_minimum',
            'adjective_penalty': 'score_adjective_penalty',
            'l35_penalty': 'score_l35_penalty',
            'single_char_platform': 'score_single_char_platform',
            'high_freq_bonus': 'score_high_freq_bonus',
            'med_freq_bonus': 'score_med_freq_bonus',
            'plausible_char_penalty': 'score_plausible_char_penalty',
            'max_consecutive_blank_paragraphs': 'max_consecutive_blank_paragraphs',
            'long_text_threshold_chars': 'long_text_threshold_chars',
            'context_window_chars': 'context_window_chars',
            'min_candidate_length': 'min_candidate_length',
            'deep_search_threshold': 'deep_search_threshold',
            'l4_search_timeout': 'l4_search_timeout',
            'auto_verify': 'l4_auto_verify',
        }

        # 数值阈值
        for json_key, value in flat.items():
            if json_key.startswith('_'):
                continue
            field_name = _key_map.get(json_key)
            if field_name is not None:
                result[field_name] = value
            else:
                warnings.warn(
                    f'[GEHD config] 未知的阈值键 "{json_key}" → 已忽略。'
                    f'请检查 config/thresholds.json 中的键名是否正确。',
                    stacklevel=2,
                )

        # frozenset 字段（来自 l3_behavior 节）
        behavior = data.get('l3_behavior', {})
        frozenset_fields = {
            'single_char_platform_suffixes': 'single_char_platform_suffixes',
            'plausible_chars': 'plausible_chars',
            'plausible_char_categories': 'plausible_char_categories',
        }
        for json_key, field_name in frozenset_fields.items():
            items = behavior.get(json_key)
            if isinstance(items, list) and len(items) > 0:
                result[field_name] = frozenset(items)

        return result if result else None
    except (json.JSONDecodeError, FileNotFoundError):
        return None


# ---- 配置定位 ----


def _find_config_dir() -> Path | None:
    """定位 config/ 目录。"""
    candidates = [
        Path.cwd() / 'config',
        Path(__file__).resolve().parents[3] / 'config',  # 项目根目录
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return None


def load_config() -> GEHDConfig:
    """加载配置：JSON 优先，回退内置默认值。

    这是外部代码获取 GEHDConfig 的唯一推荐入口。
    """
    cfg_dir = _find_config_dir()
    if cfg_dir is not None:
        return GEHDConfig.from_json_dir(cfg_dir)
    return GEHDConfig.default()


# ---- 模块级默认实例（向后兼容） ----
# 在模块导入时创建，供尚未迁移到 config 参数的代码使用。
_config_instance = load_config()

# 向后兼容：导出 GEHDConfig 实例
config = _config_instance
