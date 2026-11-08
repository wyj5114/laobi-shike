#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一键启动三个投递箱的监视进程（视频 / B站 / 腾讯会议）。

中文提示都在这里输出，bat 只做纯 ASCII 的转发，避免 cmd 按码页解析中文出错。
"""
import os
import socket
import subprocess
import sys
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, "backend", ".venv", "Scripts", "python.exe")

JOBS = [
    ("SHIKE-VIDEO", "batch_parse.py", r"D:\dsh日常工作区\视频解析\输入"),
    ("SHIKE-BILI", "bili_parse.py", r"D:\dsh日常工作区\B站解析\输入"),
    ("SHIKE-MEETING", "meeting_parse.py", r"D:\dsh日常工作区\腾讯会议解析\输入"),
]


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.6)
        return s.connect_ex(("127.0.0.1", port)) == 0


def running(script):
    """用 WMIC/CIM 不方便，这里用命令行匹配判断是否已在跑。"""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Select-Object -ExpandProperty CommandLine"],
            capture_output=True)
        text = (out.stdout or b"").decode("utf-8", "replace")
        return script in text
    except Exception:
        return False


def main():
    print()
    print("  ================================================")
    print("   一键监视：视频 / B站 / 腾讯会议 三个投递箱")
    print("  ================================================")
    print()

    print("  [1/3] 检查后端服务 127.0.0.1:8484 ...")
    if port_open(8484):
        print("        已在运行")
    else:
        print("        没在跑，正在启动（约 20 秒）...")
        ps = os.path.join(ROOT, "start_dev.ps1")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", ps], capture_output=True)
        for _ in range(40):
            if port_open(8484):
                break
            time.sleep(1)
        print("        后端就绪" if port_open(8484) else "        后端没起来，视频/B站可能失败")

    print("  [2/3] 启动监视进程（窗口会最小化到任务栏）...")
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 7  # SW_SHOWMINNOACTIVE
    started = 0
    skipped = []
    for title, script, inbox in JOBS:
        if not os.path.isfile(os.path.join(ROOT, script)):
            skipped.append(script)
            continue
        if running(script):
            print(f"        {script} 已在运行，跳过")
            continue
        subprocess.Popen([PY, os.path.join(ROOT, "_watcher.py"), title,
                          os.path.join(ROOT, script), "--loop", "--interval", "60"],
                         cwd=ROOT, creationflags=subprocess.CREATE_NEWCONSOLE
                         if hasattr(subprocess, "CREATE_NEWCONSOLE") else 0x00000010,
                         startupinfo=si)
        print(f"        已启动 {script}  →  窗口标题 {title}")
        started += 1
    if skipped:
        print(f"        （本仓库没有这些脚本，已跳过：{', '.join(skipped)}）")

    print("  [3/3] 完成。" + ("" if started else "（三个都在跑，无需重复启动）"))
    print()
    print("  ------------------------------------------------")
    print("   现在把东西丢进这三个文件夹就会自动处理：")
    print()
    for _, _, inbox in JOBS:
        print("     " + inbox)
    print()
    print("   结果在各自的「输出」文件夹里。")
    print("   停止：双击桌面「停止监视」，或关掉任务栏上的")
    print("   SHIKE-VIDEO / SHIKE-BILI / SHIKE-MEETING 三个窗口。")
    print("  ------------------------------------------------")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
