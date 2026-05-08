"""核心核查引擎

子模块：
  config    — 配置常量（阈值、魔术字符串、白/黑名单、正则模式）
  layers/   — L1~L4 各层规则引擎
  extractors/ — 文本提取与预处理
  scorers/  — 评分逻辑
  checker   — 主核查流程（gehd_check 入口）
"""
