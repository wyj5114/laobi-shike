#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""一次性解析的启动器：先打中文说明，再跑对应脚本。

用法：_once.py <目标脚本> [参数...]
- 不带参数双击：链接类的会先让你粘贴链接（不用新建 txt）。
- 把文件拖到 bat 图标上：参数会传进来，只处理这一个。

bat 里一个汉字都不写，避免 cmd 按码页解析中文把命令行截断。
"""
import os
import subprocess
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
DRYRUN = os.environ.get("SHIKE_DRYRUN") == "1"

INFO = {
    "batch_parse.py": ("本地视频 / 音频",
                       r"D:\dsh日常工作区\视频解析\输入",
                       r"D:\dsh日常工作区\视频解析\输出",
                       (".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".ts",
                        ".m4v", ".webm", ".mp3", ".m4a", ".wav", ".flac")),
    "bili_parse.py": ("B 站链接",
                      r"D:\dsh日常工作区\B站解析\输入",
                      r"D:\dsh日常工作区\B站解析\输出",
                      (".txt", ".url", ".md", ".webloc")),
    "meeting_parse.py": ("腾讯会议回放链接",
                         r"D:\dsh日常工作区\腾讯会议解析\输入",
                         r"D:\dsh日常工作区\腾讯会议解析\输出",
                         (".txt", ".url", ".md", ".webloc")),
}


def pending(inbox, exts):
    try:
        return [n for n in sorted(os.listdir(inbox))
                if os.path.isfile(os.path.join(inbox, n)) and n.lower().endswith(exts)]
    except OSError:
        return []


def ask_links(target, inbox, exts):
    """链接类投递箱：让用户直接粘贴。返回要传给脚本的参数列表。"""
    print("   直接粘贴链接，回车确认（留空 = 处理输入箱里已有的文件）")
    if target == "meeting_parse.py":
        print("   腾讯会议：先粘链接，再粘密码（没密码就直接回车）")
    else:
        print("   B 站：一行一个链接，可以一次粘多条")
    print()
    try:
        raw = input("   链接> ").strip()
    except (EOFError, KeyboardInterrupt):
        return []
    if not raw or not raw.lower().startswith("http"):
        if raw:
            print("   这不像链接，按输入箱模式处理")
        return []

    if target == "meeting_parse.py":
        try:
            pwd = input("   密码（没有就回车） > ").strip()
        except (EOFError, KeyboardInterrupt):
            pwd = ""
        return [raw + (f"\n密码：{pwd}" if pwd else "")]

    links = [l.strip() for l in raw.replace("，", "\n").replace(",", "\n").splitlines() if l.strip()]
    return links


def main():
    target = os.path.basename(sys.argv[1])
    args = sys.argv[2:]
    label, inbox, outbox, exts = INFO.get(target, (target, "", "", ()))

    print()
    print("  ================================================")
    print(f"   一次性解析：{label}")
    print("  ================================================")
    print()
    print(f"   输入箱：{inbox}")
    print(f"   输出箱：{outbox}")
    print()

    if not args and target in ("bili_parse.py", "meeting_parse.py"):
        args = ask_links(target, inbox, exts)

    if args:
        shown = " / ".join(a.replace("\n", " ") for a in args)
        print(f"   本次处理：{shown[:140]}")
    else:
        have = pending(inbox, exts) if exts else []
        print(f"   本次处理输入箱里所有待办文件（当前 {len(have)} 个）")
    print()
    print("  ------------------------------------------------")
    sys.stdout.flush()

    if DRYRUN:
        print("   [DRYRUN] argv =", [target] + args)
        return 0

    rc = subprocess.call([sys.executable, os.path.join(ROOT, target)] + args, cwd=ROOT)
    print("  ------------------------------------------------")
    print("   结束。" + ("成功。" if rc == 0 else f"有失败项，退出码 {rc}，看上面的报错或 运行日志.txt"))
    print()
    return rc


if __name__ == "__main__":
    sys.exit(main())
