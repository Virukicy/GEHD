#!/bin/bash
# GEHD — 文档幻觉核查工具 启动脚本
# macOS: Finder 双击即可启动，无需终端
cd "$(dirname "$0")"
/opt/anaconda3/bin/python3 -m hallucination_checker.gui
