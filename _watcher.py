#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""监视进程包装器：设置控制台标题后启动目标脚本。

用法：_watcher.py <窗口标题> <目标脚本> [参数...]
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
title = sys.argv[1]
target = sys.argv[2]
args = sys.argv[3:]

try:
    os.system(f"title {title}")
except Exception:
    pass

sys.exit(subprocess.call([sys.executable, target] + args, cwd=ROOT))
