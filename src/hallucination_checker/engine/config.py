"""
GEHD 全局配置 —— 所有常量、阈值、白/黑名单、正则模式的集中管理。

这个模块是"设置中心"：引擎的每一层都从这里读取参数。

配置加载优先级：
  1. config/*.json（外部化配置）— 优先使用
  2. 模块内置默认值 — JSON 文件不存在或格式错误时回退

P0-5 已完成外部化。用户直接编辑 config/ 下的 JSON 文件即可修改配置，
无需改动 Python 代码。
"""

import json
from pathlib import Path

# ============================================================
# 版本信息
# ============================================================
GEHD_VERSION = "0.1.1"
GEHD_VERSION_DATE = "2026-05-08"
GEHD_VERSION_HASH = "v011-patch-s1234"

# ============================================================
# 分数阈值
# ============================================================
SCORE_HIGH_THRESHOLD = 65      # 高危线
SCORE_MEDIUM_THRESHOLD = 45    # 中危线
SCORE_MINIMUM = 10             # 最低分数底线
SCORE_ADJECTIVE_PENALTY = 30   # 形容词前缀降分
SCORE_L35_PENALTY = 30         # L3.5 形容词降分幅度
SCORE_SINGLE_CHAR_PLATFORM = 15  # 单字平台加分（购/宝/东）
SCORE_HIGH_FREQ_BONUS = 10     # 高频加分（count>=3）
SCORE_MED_FREQ_BONUS = 3       # 中频加分（count>=2）
SCORE_PLAUSIBLE_CHAR_PENALTY = -10  # 可信字符降分

# ============================================================
# L4 协议常量
# ============================================================
L4_STATUS_PENDING = 'pending_verification'
L4_VERDICT_REAL = 'verified_real'
L4_VERDICT_FAKE = 'verified_fake'
L4_VERDICT_MANUAL = 'need_manual_check'
L4_VERDICT_UNABLE = 'unable_to_verify'
L4_QUEUE_SUFFIX = '_l4_queue.json'
L4_CACHE_SUFFIX = '_l4_cache.json'

# ============================================================
# 文本处理参数
# ============================================================
MAX_CONSECUTIVE_BLANK_PARAGRAPHS = 3
LONG_TEXT_THRESHOLD_CHARS = 300
CONTEXT_WINDOW_CHARS = 10
MIN_CANDIDATE_LENGTH = 2
DEEP_SEARCH_THRESHOLD = 55  # L4 深度搜索分数线

# ============================================================
# L1: 白名单 —— 已知真实存在的专有名词，直接放行
# ============================================================
WHITELIST: set[str] = {
    # --- 电商平台/互联网 ---
    "淘宝", "天猫", "京东", "拼多多", "PDD", "TB",
    "抖音", "小红书", "闲鱼", "苏宁", "国美",
    "美团", "美团龙珠", "饿了么", "滴滴", "支付宝", "微信支付", "微信",
    # --- 科技公司（全球） ---
    "Apple", "苹果", "华为", "小米", "OPPO", "vivo",
    "微软", "谷歌", "Google", "百度", "阿里", "阿里巴巴", "腾讯",
    "字节跳动", "网易", "携程", "去哪儿", "58同城",
    "OpenAI", "Anthropic", "Meta", "Facebook", "Amazon",
    "DeepMind", "NVIDIA", "英伟达", "AMD", "Intel", "英特尔",
    # --- 汽车品牌 ---
    "五菱宏光", "五菱", "长安", "长城", "吉利", "比亚迪",
    "丰田", "本田", "大众", "奔驰", "宝马", "奥迪",
    "特斯拉", "Tesla", "蔚来", "理想", "小鹏",
    # --- AI/具身智能/机器人 ---
    "智元机器人", "智元", "它石智航",
    "龙旗科技",
    "宇树科技", "傅利叶智能", "银河通用",
    "商汤", "旷视", "云从科技", "依图",
    "月之暗面", "MiniMax", "智谱AI", "百川智能",
    "零一万物", "阶跃星辰", "深度求索", "DeepSeek",
    "Kimi", "通义千问", "文心一言", "豆包",
    "科大讯飞", "iFLYTEK", "讯飞",
    "36氪", "钛媒体", "投资界", "PitchBook",
    "高瓴创投", "高瓴", "红杉中国", "红杉资本", "红杉",
    "启明创投", "线性资本", "蓝驰创投", "中金资本",
    "IDG资本", "经纬中国", "真格基金",
    # --- 学术机构/高校 ---
    "斯坦福大学", "斯坦福", "麻省理工", "MIT", "哈佛大学",
    "清华大学", "北京大学", "浙江大学", "复旦大学", "上海交通大学",
    "中国科学技术大学", "中科大", "南京大学", "武汉大学",
    "中山大学", "华中科技大学", "西安交通大学",
    "同济大学", "南开大学", "天津大学", "山东大学",
    "四川大学", "电子科技大学", "成电",
    "北京航空航天大学", "北航", "北京理工大学", "北理工",
    "北京师范大学", "北师大", "中国人民大学", "人大",
    "上海财经大学", "上财",
    "中国地质大学", "地质大学", "地大",
    "悉尼大学", "USYD", "悉尼",
    # --- 政府机构/组织 ---
    "国家网信办", "网信办", "工信部", "发改委", "教育部",
    "中国科学院", "中科院", "中国工程院",
    "世界卫生组织", "WHO", "ISO", "IEEE", "ACM",
    "联合国", "欧盟", "央视网", "央视", "CCTV",
    "世界互联网大会",
    # --- 用户自定义 ---
    "未来萤火虫",
    # --- 编程/技术 ---
    "python-docx", "Python", "JavaScript", "Node.js",
    "Windows", "macOS", "Linux", "iOS", "Android",
    # --- 地理 ---
    "中国", "北京", "上海", "广州", "深圳", "杭州",
    "南昌", "香港", "绵阳", "无锡", "南京",
}

# ============================================================
# L2: 黑名单 —— 历史已确认的幻觉/虚构词汇，直接报错
# ============================================================
BLACKLIST: list[str] = [
    "母丑", "母丑购", "母丑京东", "母丑商城",
]

# ============================================================
# L3: 实体提取规则 —— (正则, 类别名, 基础分)
# ============================================================
ENTITY_PATTERNS: list[tuple[str, str, int]] = [
    # 电商平台名
    (r'([\u4e00-\u9fff]{1,3}(?:购|商城|超市|百货|优选|特卖|专营|官方店|旗舰店))',
     '电商平台名', 60),
    # 公司机构名
    (r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,6}(?:公司|集团|企业|科技|股份|有限|控股|投资|基金|银行|保险|证券|信托))',
     '公司机构名', 50),
    # 学术机构名
    (r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,5}(?:大学|学院|学校|研究院|研究所|实验室|医院|中心|协会|学会|组织))',
     '学术机构名', 45),
    # 产品品牌名
    (r'\b([\u4e00-\u9fff]{2,5}(?:牌|系列|型号|版))\b',
     '产品品牌名', 40),
    # 政府机构名
    (r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,6}(?:局|委员会|办公厅|管理处|监管局|指挥部|办公室))',
     '政府机构名', 48),
    # 行业协会/联合会/联盟
    (r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{3,8}(?:行业协会|联合会|促进会|联盟|商会|公会))',
     '行业组织名', 45),
    # 半导体/微电子类公司
    (r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,6}(?:微电子|半导体|集成电路|光电子))',
     '半导体企业名', 50),
    # 产品型号（英文+数字）
    (r'([A-Z][A-Za-z0-9]*[-–][A-Z0-9][A-Za-z0-9]*)',
     '产品型号', 42),
    # 人名+称谓
    (r'(?:^|[^\u4e00-\u9fff])([\u4e00-\u9fff]{2,3})(?:先生|女士|小姐|博士|教授|老师|工程师|经理|总监|总|董)',
     '人名+称谓', 35),
    # 地名
    (r'(?:^|[^\u4e00-\u9fff]|位于|在|于|至|往|从|的)([\u4e00-\u9fff]{2,4}(?:省|市|县|区|镇|乡|村|路|街|道|广场|大厦|写字楼|商场|机场|车站|港口))',
     '地名', 30),
    # 会议/活动/计划名称
    (r'["\u300c\u300d\u201c\u201d]([\u4e00-\u9fff]{2,10})(?:计划|行动|工程|倡议|战略|峰会|论坛|大会|博览会)["\u300c\u300d\u201c\u201d]',
     '会议/IP名', 32),
    # 引用名称/IP名
    (r'["\u300c\u300d\u201c\u201d]([\u4e00-\u9fff]{2,8})["\u300c\u300d\u201c\u201d]',
     '引用名称/IP名', 25),
    # 英文机构/品牌名
    (r'\b([A-Z][a-z]{2,}(?:[ -][A-Z][a-z]{2,}){1,2})(?: Inc| Corp| LLC| Ltd| Co| Group)?\b',
     '英文机构/品牌名', 40),
]

# ============================================================
# L2.5: 非实体幻觉检测规则
# ============================================================
L25_PATTERNS: list[tuple[str, str, int]] = [
    # 可疑统计金额
    (r'(\d+(?:\.\d+)?(?:万亿|亿|万)?(?:元|美元|人民币|欧元))',
     '可疑统计金额', 48),
    # 可疑百分比数据
    (r'(?:增长率?|增速|增幅|涨幅|同比|环比|市占率?|占有率|渗透率|转化率|复购率)[超达]?\s*(\d+(?:\.\d+)?%)',
     '可疑百分比数据', 45),
    # 可疑规模描述
    (r'(?<!已)(?<!完成)(?:达|约|将近|超过|突破)\s*(\d+(?:\.\d+)?(?:万亿|亿|万)?\s*(?:元|美元|人|户|家|台|套))',
     '可疑规模描述', 42),
    # 权威引述
    (r'据\s*([\u4e00-\u9fff]{2,4}(?:教授|博士|院士|CEO|总裁|总[经理裁]|部长|司长|局长|主任|所长))\s*(?:称|表示|透露|指出|强调|透露|宣布)',
     '权威引述', 50),
    # 直接引语（待核实）
    (r'["\u201c]((?:(?:[\u4e00-\u9fff]{1,3}(?:教授|博士|院士|CEO|总裁|总[经理裁]|部长|司长|局长|主任|所长|先生|女士))'
     r'|(?:[\u4e00-\u9fff]{2,6}(?:公司|集团|研究院|研究所|大学|学院|银行|部委|协会|学会))'
     r'|(?:\d+(?:\.\d+)?(?:%|(?:万亿|亿|万)?(?:元|美元|人|家)))'
     r'|(?:20\d{2}年|[一二三四]季度|Q[1-4]|[上下本]月|今年|去年|前年)'
     r').{0,50}[^"\u201d]{5,})["\u201d]',
     '直接引语(待核实)', 35),
    # 时间线引用
    (r'(?:于|在|预计|将于|将在|计划于)\s*(20\d{2}年(?:[一二三四]?季度|Q[1-4]|[1-12]月))',
     '时间线引用', 38),
    # 完成时间声明
    (r'(?:已于?|已在|已经完成|已完成|成功实现)\s*(20\d{2}(?:年[1-12]月|[/-]\d{1,2}))',
     '完成时间声明', 40),
]

# L2.5 排除：已知真实且无需核查的常见表述
L25_EXCLUDE_PHRASES: set[str] = {
    "GDP", "CPI", "PMI", "GDP增长率",
    "2026年", "2025年", "2024年", "2023年",
}

# ============================================================
# 噪音前缀 & 排除词表
# ============================================================
NOISE_PREFIXES: tuple[str, ...] = (
    '在', '的', '是', '有', '被', '从', '向', '对', '为', '由',
    '把', '与', '和', '及', '或', '而', '但', '若', '如', '因',
)

ENTITY_SUFFIXES_FOR_EXCLUSION: tuple[str, ...] = (
    '中心', '公司', '集团', '研究院', '研究所', '实验室',
    '协会', '学会', '管理局', '委员会', '办公室',
)

EXCLUDE_WORDS: set[str] = {
    "采购", "采购完毕", "采购日", "采购建议",
    "购置", "购买",
    "弹力网", "电网", "水电网", "断网", "力网",
    "上网", "在电商平台",
    "购物平台", "电商平台", "交易平台", "销售平台", "服务平台",
    "共享平台", "云平台", "技术平台", "数据平台",
    "购物中心", "大型商场", "综合百货",
    "快乐购", "快乐购的", "正在购",
    "这意味着企业", "已经走出了实验室", "和规模效应的公司",
    "获投企业", "科大等高校及企业", "京东全链路", "备中国地质大学",
    "权威科技", "领先科技", "知名科技", "大型科技", "专业科技", "顶级科技",
    "大型企业",
    "车规级芯片", "训练芯片", "推理芯片", "AI芯片", "算力芯片",
    "智能学院",
    "机构的战略投资", "用层仍有大量投资", "硅谷初创企业",
    "包括多家上市公司", "学院联合多家企业",
    "Test Suite", "Robotics", "Machine Intelligence",
    "Suite", "Machine",
    "子人工智能实验室", "身智能联合实验室", "关村的灵境研究院",
    "年国内", "据财新报道", "技术路", "公开报道",
}

ADJECTIVE_PREFIXES: set[str] = {
    "权威", "领先", "知名", "大型", "专业", "顶级", "头部",
    "新兴", "热门", "主流", "重要", "核心", "关键", "主要",
    "多家", "众多", "部分", "相关", "其他", "上述", "某些",
}

# ============================================================
# JSON 外部化配置加载器
# ============================================================
# 如果 config/ 目录下有对应的 JSON 文件，则使用外部化配置覆盖内置默认值。
# 这样用户编辑 JSON 即可修改配置，无需碰 Python 代码。


def _find_config_dir() -> Path | None:
    """定位 config/ 目录。

    搜索顺序：
      1. 当前工作目录下的 config/
      2. 本文件向上 4 级（项目根目录）下的 config/
    """
    candidates = [
        Path.cwd() / 'config',
        Path(__file__).resolve().parent.parent.parent.parent / 'config',
    ]
    for p in candidates:
        if p.is_dir():
            return p
    return None


def _load_json_list(filepath: Path, key: str) -> list[str] | None:
    """从 JSON 文件中加载字符串列表。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        items = data.get(key, [])
        if isinstance(items, list) and len(items) > 0:
            return items
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def _load_json_patterns(filepath: Path, key: str) -> list[tuple[str, str, int]] | None:
    """从 JSON 文件中加载 (pattern, category, score) 元组列表。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
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


def _load_json_thresholds(filepath: Path) -> dict | None:
    """从 JSON 文件中加载评分阈值。"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        scores = data.get('scores', {})
        text = data.get('text_processing', {})
        l4 = data.get('l4', {})
        if scores or text or l4:
            return {**scores, **text, **l4}
    except (json.JSONDecodeError, FileNotFoundError):
        pass
    return None


def _apply_external_config() -> None:
    """加载外部化配置并覆盖模块级变量。

    每种配置独立加载，失败时静默跳过（使用内置默认值）。
    使用显式变量赋值而非 globals() 魔法，确保 mypy 可追踪。
    """
    cfg_dir = _find_config_dir()
    if cfg_dir is None:
        return

    # --- 白名单 ---
    whitelist_items = _load_json_list(cfg_dir / 'whitelist.json', 'whitelist')
    if whitelist_items is not None:
        # 显式赋值：mypy 可以验证类型一致性
        _apply_whitelist(set(whitelist_items))

    # --- 黑名单 ---
    blacklist_items = _load_json_list(cfg_dir / 'blacklist.json', 'blacklist')
    if blacklist_items is not None:
        _apply_blacklist(list(blacklist_items))

    # --- 实体提取模式 ---
    entity_patterns = _load_json_patterns(cfg_dir / 'entity_patterns.json', 'patterns')
    if entity_patterns is not None:
        _apply_entity_patterns(entity_patterns)

    # --- L2.5 模式 ---
    l25_patterns = _load_json_patterns(cfg_dir / 'l25_patterns.json', 'patterns')
    if l25_patterns is not None:
        _apply_l25_patterns(l25_patterns)

    # --- 排除词 ---
    exclude_items = _load_json_list(cfg_dir / 'exclude_words.json', 'exclude_words')
    if exclude_items is not None:
        _apply_exclude_words(set(exclude_items))

    # --- 形容词前缀 ---
    adj_items = _load_json_list(cfg_dir / 'adjective_prefixes.json', 'adjective_prefixes')
    if adj_items is not None:
        _apply_adjective_prefixes(set(adj_items))

    # --- 评分阈值 ---
    thresholds = _load_json_thresholds(cfg_dir / 'thresholds.json')
    if thresholds is not None:
        _apply_thresholds(thresholds)


# ---- 显式应用函数（每个函数明确修改哪个模块变量） ----

def _apply_whitelist(items: set[str]) -> None:
    global WHITELIST
    WHITELIST = items


def _apply_blacklist(items: list[str]) -> None:
    global BLACKLIST
    BLACKLIST = items


def _apply_entity_patterns(items: list[tuple[str, str, int]]) -> None:
    global ENTITY_PATTERNS
    ENTITY_PATTERNS = items


def _apply_l25_patterns(items: list[tuple[str, str, int]]) -> None:
    global L25_PATTERNS
    L25_PATTERNS = items


def _apply_exclude_words(items: set[str]) -> None:
    global EXCLUDE_WORDS
    EXCLUDE_WORDS = items


def _apply_adjective_prefixes(items: set[str]) -> None:
    global ADJECTIVE_PREFIXES
    ADJECTIVE_PREFIXES = items


def _apply_thresholds(items: dict) -> None:
    """将阈值 dict 的键映射到模块级变量（显式白名单校验）。"""
    global SCORE_HIGH_THRESHOLD, SCORE_MEDIUM_THRESHOLD, SCORE_MINIMUM
    global SCORE_SINGLE_CHAR_PLATFORM, SCORE_L35_PENALTY
    global SCORE_HIGH_FREQ_BONUS, SCORE_MED_FREQ_BONUS
    global SCORE_PLAUSIBLE_CHAR_PENALTY
    global MAX_CONSECUTIVE_BLANK_PARAGRAPHS, LONG_TEXT_THRESHOLD_CHARS
    global CONTEXT_WINDOW_CHARS, MIN_CANDIDATE_LENGTH, DEEP_SEARCH_THRESHOLD

    # 白名单键名集合（仅验证 key 合法性，不做值映射）
    _valid_keys = {
        'HIGH_THRESHOLD', 'MEDIUM_THRESHOLD', 'MINIMUM',
        'ADJECTIVE_PENALTY',
        'SINGLE_CHAR_PLATFORM', 'L35_PENALTY',
        'HIGH_FREQ_BONUS', 'MED_FREQ_BONUS', 'PLAUSIBLE_CHAR_PENALTY',
        'MAX_CONSECUTIVE_BLANK_PARAGRAPHS', 'LONG_TEXT_THRESHOLD_CHARS',
        'CONTEXT_WINDOW_CHARS', 'MIN_CANDIDATE_LENGTH', 'DEEP_SEARCH_THRESHOLD',
    }

    for json_key, value in items.items():
        # 跳过注释键（以下划线开头）
        if json_key.startswith('_'):
            continue
        key_upper = json_key.upper()
        if key_upper in _valid_keys:
            _assign_threshold(key_upper, value)
        else:
            import warnings as _w
            _w.warn(
                f'[GEHD config] 未知的阈值键 "{json_key}" → 已忽略。'
                f'请检查 config/thresholds.json 中的键名是否正确。'
            )


def _assign_threshold(key: str, value: int) -> None:
    """显式阈值赋值——每条 if 分支都有明确的变量名，mypy 完全可追踪。"""
    global SCORE_HIGH_THRESHOLD, SCORE_MEDIUM_THRESHOLD, SCORE_MINIMUM
    global SCORE_HIGH_FREQ_BONUS, SCORE_MED_FREQ_BONUS
    global SCORE_SINGLE_CHAR_PLATFORM, SCORE_L35_PENALTY
    global SCORE_PLAUSIBLE_CHAR_PENALTY
    global MAX_CONSECUTIVE_BLANK_PARAGRAPHS, LONG_TEXT_THRESHOLD_CHARS
    global CONTEXT_WINDOW_CHARS, MIN_CANDIDATE_LENGTH, DEEP_SEARCH_THRESHOLD

    if key == 'HIGH_THRESHOLD':
        SCORE_HIGH_THRESHOLD = value
    elif key == 'MEDIUM_THRESHOLD':
        SCORE_MEDIUM_THRESHOLD = value
    elif key == 'MINIMUM':
        SCORE_MINIMUM = value
    elif key == 'ADJECTIVE_PENALTY':
        SCORE_ADJECTIVE_PENALTY = value
    elif key == 'HIGH_FREQ_BONUS':
        SCORE_HIGH_FREQ_BONUS = value
    elif key == 'MED_FREQ_BONUS':
        SCORE_MED_FREQ_BONUS = value
    elif key == 'SINGLE_CHAR_PLATFORM':
        SCORE_SINGLE_CHAR_PLATFORM = value
    elif key == 'L35_PENALTY':
        SCORE_L35_PENALTY = value
    elif key == 'PLAUSIBLE_CHAR_PENALTY':
        SCORE_PLAUSIBLE_CHAR_PENALTY = value
    elif key == 'MAX_CONSECUTIVE_BLANK_PARAGRAPHS':
        MAX_CONSECUTIVE_BLANK_PARAGRAPHS = value
    elif key == 'LONG_TEXT_THRESHOLD_CHARS':
        LONG_TEXT_THRESHOLD_CHARS = value
    elif key == 'CONTEXT_WINDOW_CHARS':
        CONTEXT_WINDOW_CHARS = value
    elif key == 'MIN_CANDIDATE_LENGTH':
        MIN_CANDIDATE_LENGTH = value
    elif key == 'DEEP_SEARCH_THRESHOLD':
        DEEP_SEARCH_THRESHOLD = value


# 模块加载时自动应用外部化配置
_apply_external_config()

