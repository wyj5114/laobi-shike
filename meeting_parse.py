#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""腾讯会议回放解析流水线

投递箱：D:\\dsh日常工作区\\腾讯会议解析\\输入   （放 .txt：链接 + 密码）
输出：  D:\\dsh日常工作区\\腾讯会议解析\\输出\\<会议名>\\

用法：
  python meeting_parse.py                处理输入文件夹里所有待办文件
  python meeting_parse.py <文件或链接>    处理单个
  python meeting_parse.py --loop         常驻监视（默认每 60 秒）
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

import numpy as np
import requests
from PIL import Image

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------- 配置 ----------
# 所有路径都可用环境变量覆盖，默认值就是本机布局，换机器时按需改这里或设环境变量：
#   SHIKE_MEETING_DIR  投递箱根目录（下面会自动建 输入/已处理/失败/输出）
#   SHIKE_PROXY        模型代理地址      SHIKE_MODEL  模型名
#   SHIKE_PROXY_KEY    代理密钥（优先读环境变量，其次读同目录 _local_key.txt）
ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.environ.get("SHIKE_MEETING_DIR") or r"D:\dsh日常工作区\腾讯会议解析"
IN_DIR = os.path.join(WORK, "输入")
DONE_DIR = os.path.join(IN_DIR, "已处理")
FAIL_DIR = os.path.join(IN_DIR, "失败")
OUT_DIR = os.path.join(WORK, "输出")
LOG_FILE = os.path.join(WORK, "运行日志.txt")

PROFILE = os.environ.get("SHIKE_PROFILE") or os.path.join(ROOT, "_edge_profile")
FFMPEG = os.environ.get("SHIKE_FFMPEG") or os.path.join(ROOT, "tools", "ffmpeg", "bin", "ffmpeg.exe")
NODE = os.environ.get("SHIKE_NODE") or r"D:\DSH\resources\runtime\primary-runtime\dependencies\node\bin\node.exe"
LO_CLI = os.environ.get("SHIKE_LO_CLI") or (
    r"D:\DSH\resources\app.asar.unpacked\dsh\node_modules"
    r"\@deepseek-ai\libreoffice-kit\lib\cli.js")

PROXY = os.environ.get("SHIKE_PROXY") or "http://127.0.0.1:7863/v1"
MODEL = os.environ.get("SHIKE_MODEL") or "cn:deepseek-v4.1-flash"


def _load_key():
    """密钥不入库：环境变量 SHIKE_PROXY_KEY 优先，其次同目录 _local_key.txt。"""
    for env in ("SHIKE_PROXY_KEY", "WB_API_KEY"):
        v = os.environ.get(env)
        if v and v.strip():
            return v.strip()
    p = os.path.join(ROOT, "_local_key.txt")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    return ""


PROXY_KEY = _load_key()

SLIDE_STEP = 15          # 抽帧间隔（秒）
SLIDE_DIFF = 3.2         # 画面变化阈值
SLIDE_MAX = 110          # 最多保留张数
MIN_GAP = 45             # 相邻关键帧最小间隔（秒）

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Edg/126.0.0.0")

def log(*a):
    msg = " ".join(str(x) for x in a)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def hhmmss(ms_or_sec, ms=True):
    sec = int(float(ms_or_sec) // 1000) if ms else int(float(ms_or_sec))
    return f"{sec // 3600:02d}:{sec % 3600 // 60:02d}:{sec % 60:02d}"


def safe_name(s, fallback="会议"):
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", (s or "").strip())
    s = re.sub(r"\s+", " ", s).strip(" .")
    return (s[:60] or fallback)


def unique_dir(base, name):
    p = os.path.join(base, name)
    n = 2
    while os.path.exists(p):
        p = os.path.join(base, f"{name}_{n}")
        n += 1
    return p


# ---------- 1. 解析投递文件 ----------
def parse_input(text):
    m = re.search(r"https?://meeting\.tencent\.com/[^\s，,、）)】\"'<>]+", text)
    url = m.group(0).rstrip("。.,，") if m else None
    pwd = None
    m2 = re.search(r"(?:密码|口令|passcode|pwd|password)\s*[:：=]?\s*([A-Za-z0-9]{3,16})",
                   text, re.I)
    if m2:
        pwd = m2.group(1)
    else:
        for line in text.splitlines():
            s = line.strip()
            if re.fullmatch(r"[A-Za-z0-9]{4,16}", s) and s != url:
                pwd = s
                break
    return url, pwd


# ---------- 2. 登录 + 抓逐字稿 + 抓视频直链 ----------
def grab(url, pwd):
    from playwright.sync_api import sync_playwright

    os.environ["TEMP"] = os.path.join(ROOT, "_pw_tmp")
    os.environ["TMP"] = os.environ["TEMP"]
    os.makedirs(os.environ["TEMP"], exist_ok=True)

    bodies, media, meta = [], [], {}

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, channel="msedge", headless=False,
            viewport={"width": 1500, "height": 860}, locale="zh-CN",
            args=["--autoplay-policy=no-user-gesture-required",
                  "--disable-blink-features=AutomationControlled"],
        )

        def on_resp(resp):
            u = resp.url
            try:
                if re.search(r"\.mp4(\?|$)", u) or ".m3u8" in u:
                    if u not in media:
                        media.append(u)
                        log("  发现视频流:", u.split("?")[0][-60:])
                    return
                if "minutes/detail" in u or "common-record-info" in u:
                    body = resp.text()
                    if not body.startswith("{"):
                        return
                    bodies.append(body)
                    j = json.loads(body)
                    paras = ((j.get("minutes") or {}).get("paragraphs")) or []
                    if paras:
                        log(f"  逐字稿分页: {len(paras)} 段 "
                            f"{hhmmss(paras[0]['start_time'])} → {hhmmss(paras[-1]['end_time'])}")
                    for k in ("subject", "title", "meeting_topic", "record_name"):
                        v = j.get(k) or (j.get("data") or {}).get(k) if isinstance(j.get("data"), dict) else j.get(k)
                        if isinstance(v, str) and v.strip():
                            meta.setdefault(k, v.strip())
            except Exception:
                pass

        ctx.on("response", on_resp)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        log("  打开:", url)
        page.goto(url, wait_until="domcontentloaded", timeout=90000)
        page.wait_for_timeout(5000)

        # 密码
        if pwd:
            for sel in ("input[type=password]", "input[placeholder*='密码']", "input[placeholder*='口令']"):
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill(pwd)
                    log("  已填密码")
                    for label in ("查看", "进入", "确认", "提交", "加入"):
                        b = page.query_selector(f"text={label}")
                        if b and b.is_visible():
                            b.click()
                            log("  点击:", label)
                            break
                    page.wait_for_timeout(5000)
                    break

        # 进入播放器
        for label in ("前往查看", "查看回放", "播放"):
            try:
                el = page.query_selector(f"text={label}")
                if el and el.is_visible():
                    el.click()
                    log("  点击:", label)
                    page.wait_for_timeout(7000)
                    break
            except Exception:
                pass

        # 等登录/播放器就绪
        for i in range(60):
            if bodies or media:
                break
            if i == 10:
                log("  …等待页面就绪（若需要登录，请在弹出的浏览器里登录，最多等 8 分钟）")
            page.wait_for_timeout(8000)

        # 逐字稿标签
        for label in ("逐字稿", "转写", "文字记录"):
            try:
                el = page.query_selector(f"text={label}")
                if el and el.is_visible():
                    el.click()
                    log("  打开:", label)
                    page.wait_for_timeout(6000)
                    break
            except Exception:
                pass

        # 滚动加载全部分页
        try:
            box = page.evaluate("""() => {
                const c = [...document.querySelectorAll('div')].filter(d => {
                    const s = getComputedStyle(d);
                    return (s.overflowY === 'auto' || s.overflowY === 'scroll')
                        && d.scrollHeight > d.clientHeight + 200;
                }).sort((a,b) => b.scrollHeight - a.scrollHeight);
                if (!c.length) return null;
                const d = c[0], r = d.getBoundingClientRect();
                window.__se = d;
                return {x: r.left + r.width/2, y: r.top + Math.min(300, r.height/2)};
            }""")
            if box:
                page.mouse.move(box["x"], box["y"])
        except Exception:
            pass

        for i in range(60):
            page.mouse.wheel(0, -4000)
            page.wait_for_timeout(700)
            if i % 10 == 9:
                page.evaluate("() => { const d = window.__se; if (d) d.scrollTop = 0; }")
        for i in range(20):
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(500)

        try:
            meta["page_title"] = page.title()
        except Exception:
            pass
        ctx.close()

    # 合并逐字稿
    paras = {}
    for b in bodies:
        try:
            j = json.loads(b)
        except Exception:
            continue
        for pa in (j.get("minutes") or {}).get("paragraphs") or []:
            paras[pa["pid"]] = pa
    ordered = sorted(paras.values(), key=lambda x: x["start_time"])

    lines = []
    for pa in ordered:
        who = (pa.get("speaker") or {}).get("user_name") or "发言人"
        txt = "".join(w.get("text", "") for s in (pa.get("sentences") or [])
                      for w in (s.get("words") or []))
        if not txt:
            txt = "".join(s.get("text", "") for s in (pa.get("sentences") or []))
        if txt.strip():
            lines.append(f"[{hhmmss(pa['start_time'])}] {who}：{txt.strip()}")

    return {"bodies": bodies, "media": media, "meta": meta,
            "transcript_lines": lines,
            "coverage": (hhmmss(ordered[0]["start_time"]), hhmmss(ordered[-1]["end_time"]))
            if ordered else ("", "")}


# ---------- 3. 下载视频 ----------
def download_videos(media, vdir):
    os.makedirs(vdir, exist_ok=True)
    got = []
    for u in media:
        if ".m3u8" in u:
            continue
        tag = "共享屏幕" if "screen" in u.lower() else ("发言人" if "speaker" in u.lower() else None)
        if not tag:
            tag = "视频" if not got else f"视频{len(got) + 1}"
        path = os.path.join(vdir, f"{tag}.mp4")
        if os.path.exists(path) and os.path.getsize(path) > 1 << 20:
            log(f"  已存在，跳过: {tag}.mp4")
            got.append(path)
            continue
        log(f"  下载 {tag}.mp4 ...")
        try:
            with requests.get(u, headers={"User-Agent": UA,
                                          "Referer": "https://meeting.tencent.com/"},
                              stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(path + ".part", "wb") as f:
                    for chunk in r.iter_content(1 << 19):
                        if chunk:
                            f.write(chunk)
            os.replace(path + ".part", path)
            log(f"  完成 {tag}.mp4  {os.path.getsize(path) / 1048576:.0f} MB")
            got.append(path)
        except Exception as e:
            log(f"  !! {tag} 下载失败: {type(e).__name__} {str(e)[:100]}")
    return got


# ---------- 4. 生成笔记 ----------
def _fold_system(messages):
    """本地代理会丢弃 system 消息，统一折进第一条 user 消息。"""
    sys_txt = "\n\n".join(str(m.get("content") or "") for m in messages
                          if m.get("role") == "system").strip()
    rest = [dict(m) for m in messages if m.get("role") != "system"]
    if not sys_txt:
        return rest or [{"role": "user", "content": ""}]
    if rest:
        rest[0]["content"] = sys_txt + "\n\n" + str(rest[0].get("content") or "")
        return rest
    return [{"role": "user", "content": sys_txt}]


def chat(messages, temperature=0.3, stream=False):
    """调用本地代理；503/超时自动退避重试。"""
    messages = _fold_system(messages)
    body = {"model": MODEL, "temperature": temperature, "messages": messages, "stream": stream}
    err = None
    for attempt in range(4):
        try:
            return _chat_once(body, stream)
        except Exception as e:
            err = e
            wait = (3, 8, 20, 40)[min(attempt, 3)]
            print(f"    !! 请求失败（{type(e).__name__}: {str(e)[:70]}），{wait}s 后重试", flush=True)
            time.sleep(wait)
    raise err


def _chat_once(body, stream):
    if not stream:
        r = requests.post(PROXY + "/chat/completions",
                          headers={"Authorization": f"Bearer {PROXY_KEY}"},
                          json=body, timeout=900)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    out = []
    with requests.post(PROXY + "/chat/completions",
                       headers={"Authorization": f"Bearer {PROXY_KEY}"},
                       json=body, stream=True, timeout=1800) as r:
        r.raise_for_status()
        for raw in r.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8", "replace")
            if not line.startswith("data: "):
                continue
            d = line[6:].strip()
            if d == "[DONE]":
                break
            try:
                j = json.loads(d)
            except Exception:
                continue
            piece = ((j.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
            if piece:
                out.append(piece)
                if len(out) % 60 == 0:
                    print(f"    …{sum(len(x) for x in out)} 字", flush=True)
    return "".join(out).strip()


def fix_latex(md):
    md = re.sub(r"\\\[(.+?)\\\]", lambda m: "\n$$\n" + m.group(1).strip() + "\n$$\n", md, flags=re.S)
    md = re.sub(r"\\\((.+?)\\\)", lambda m: "$" + m.group(1).strip() + "$", md, flags=re.S)
    md = md.replace("\\[", "\n$$\n").replace("\\]", "\n$$\n")
    md = md.replace("\\(", "$").replace("\\)", "$")
    md = md.replace("\\dfrac", "\\frac").replace("\\tfrac", "\\frac")
    return md


META_LINE = re.compile(
    r"^\s*(如果需要|如需|需要我|要不要|我可以|希望这份|以上就是|这份笔记|如有需要|"
    r"你还想|还想我|是否需要|可以继续|后续可以)")

CHUNK_SYSTEM = """你是课堂笔记提炼员。用户给你一段带时间戳的语音识别逐字稿（可能很长），
你要把它压成高密度知识点条目，供后续合并成分节笔记。

只输出 Markdown 片段（不要大标题、不要寒暄、不要结尾征求意见），按讲课顺序写：

- **概念/公式**：写清定义式、条件、结论；公式用 $...$（行内）或 $$...$$（独立行）的 LaTeX。
- **例题**：逐题记录——题目原话、思路、关键步骤算式、答案；每题前面标时间戳 `[hh:mm:ss]`。
- **讲师强调**：易错点、口诀、记忆技巧，用「⚠️」开头。
- **口误修正**：语音识别错的专业术语按学科常识改正，拿不准的加（疑似）。

看不到的内容不要编。宁可条目少，不要凑字数。"""

MERGE_SYSTEM = """你是资深课程笔记主编。用户给你一份「分段提炼稿」（同一堂课按时间分段整理的知识点条目），
请合并成一份结构完整、可直接复习和转发的笔记。

硬性要求：
1. 严格去重：同一知识点在不同分段重复出现，合并成一处，不要重复陈述。
2. 必须包含下列章节，标题文字照抄，顺序不变：
   # <标题> · 笔记
   > 元信息（讲师/日期/时长/来源/逐字稿覆盖范围）
   ## 一、内容全景        （一段话脉络 + 「章节→核心问题→结论」表格）
   ## 二、知识点详解      （按讲课顺序分 ### 小节：定义 / 性质公式 / 易错点 ⚠️ / 口诀）
   ## 三、例题与解法      （逐题：题目 → 思路 → 关键步骤 → 答案，标时间点。这是重点章节，不许省略或改成方法索引）
   ## 四、重点与复习清单  （必背结论 / 常考题型 / 自测问题 5~8 个，不给答案）
   ## 五、待确认 / 存疑处
3. 公式一律用 $...$ 或 $$...$$（KaTeX），禁止 \\( \\) 和 \\[ \\]。
4. 定义域值域、公式对照、等价无穷小这类内容一律做成表格。
5. 篇幅：短课 4000~6000 字；2 小时以上 9000~13000 字。宁详勿略。
6. 结尾严禁出现「如果需要我可以…」「需要我继续…」这类话；最后一行就是正文最后一条内容。"""


def _chunk(lines, max_chars=12000):
    out, cur, n = [], [], 0
    for l in lines:
        if cur and n + len(l) > max_chars:
            out.append(cur)
            cur, n = [], 0
        cur.append(l)
        n += len(l) + 1
    if cur:
        out.append(cur)
    return out


def _strip_meta(md):
    lines = md.rstrip().splitlines()
    keep = []
    for l in lines:
        if META_LINE.match(l):
            continue
        keep.append(l)
    while keep and (not keep[-1].strip() or keep[-1].strip() in ("---", "***")):
        keep.pop()
    return "\n".join(keep).strip()


def gen_note(lines, title, outdir):
    transcript = "\n".join(lines)
    if len(transcript) > 24000:
        parts = _chunk(lines)
        log(f"  逐字稿 {len(transcript)} 字，分 {len(parts)} 段精读")
        from concurrent.futures import ThreadPoolExecutor

        def one(idx_part):
            idx, ch = idx_part
            head = ch[0][:11]
            tail = ch[-1][:11]
            txt = chat([{"role": "system", "content": CHUNK_SYSTEM},
                        {"role": "user", "content": f"逐字稿第 {idx + 1} 段"
                                                    f"（{head} 至 {tail}）：\n\n" + "\n".join(ch)}],
                       temperature=0.2)
            log(f"    段 {idx + 1}/{len(parts)} 提炼完成 {len(txt)} 字")
            return f"\n\n## 分段 {idx + 1}（{head} 至 {tail}）\n\n{txt}"

        with ThreadPoolExecutor(max_workers=2) as ex:
            notes = list(ex.map(one, enumerate(parts)))
        merged = "".join(notes)
        md = chat([{"role": "system", "content": MERGE_SYSTEM},
                   {"role": "user", "content": f"课程标题：{title}\n\n分段提炼稿：\n{merged}"}],
                  temperature=0.3, stream=True)
    else:
        md = chat([{"role": "system", "content": MERGE_SYSTEM + "\n\n下面是完整逐字稿，请直接整理："},
                   {"role": "user", "content": f"课程标题：{title}\n\n逐字稿：\n\n{transcript}"}],
                  temperature=0.3, stream=True)

    md = _strip_meta(fix_latex(md))
    path = os.path.join(outdir, "笔记.md")
    open(path, "w", encoding="utf-8").write(md + "\n")
    log(f"  笔记: {len(md)} 字")
    return path


def gen_timeline(lines):
    body = "\n".join(lines)
    prompt = ("下面是一份带时间戳的逐字稿。请只输出一张 Markdown 表格，两列：时间 | 这一段讲了什么"
              "（14 字以内）。每 5~8 分钟一行，按时间顺序覆盖全程。"
              "时间列必须抄逐字稿里的 hh:mm:ss 原样（例如 00:24:01），不要写成区间。"
              "不要任何前言后语，不要代码块包裹。\n\n" + body)
    t = chat([{"role": "user", "content": prompt}], temperature=0.2)
    return re.sub(r"^```(?:markdown)?\s*|\s*```$", "", t).strip()


# ---------- 5. 课件截图 ----------
def thumb(path):
    return np.asarray(Image.open(path).convert("L").resize((64, 36)), dtype=np.float32)


def extract_slides(video, imgdir, tmpdir):
    os.makedirs(imgdir, exist_ok=True)
    os.makedirs(tmpdir, exist_ok=True)
    for f in os.listdir(tmpdir):
        if f.endswith(".jpg"):
            os.remove(os.path.join(tmpdir, f))

    log(f"  抽帧（每 {SLIDE_STEP} 秒一帧）...")
    t0 = time.time()
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", video,
                    "-vf", f"fps=1/{SLIDE_STEP},scale=1024:-1", "-q:v", "5",
                    os.path.join(tmpdir, "f_%04d.jpg")], check=False,
                   capture_output=True)
    files = sorted(f for f in os.listdir(tmpdir) if f.endswith(".jpg"))
    log(f"  抽到 {len(files)} 帧，用时 {time.time() - t0:.0f}s，开始去重")

    kept, prev, prev_t = [], None, -10 ** 9
    for i, fn in enumerate(files):
        t = i * SLIDE_STEP
        th = thumb(os.path.join(tmpdir, fn))
        diff = 999.0 if prev is None else float(np.mean(np.abs(th - prev)))
        if diff >= SLIDE_DIFF and (t - prev_t) >= MIN_GAP:
            kept.append((t, os.path.join(tmpdir, fn)))
            prev, prev_t = th, t
    if len(kept) > SLIDE_MAX:
        step = max(1, len(kept) // SLIDE_MAX)
        kept = kept[::step]
    log(f"  关键帧 {len(kept)} 张")

    items = []
    for idx, (t, path) in enumerate(kept, 1):
        h, m, s = t // 3600, t % 3600 // 60, t % 60
        name = f"{idx:02d}_{h:02d}-{m:02d}-{s:02d}.jpg"
        Image.open(path).save(os.path.join(imgdir, name), quality=88)
        items.append({"index": idx, "second": t,
                      "time": f"{h:02d}:{m:02d}:{s:02d}", "file": name})
    json.dump(items, open(os.path.join(imgdir, "index.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return items


def caption_for(items, lines):
    rows = []
    for line in lines:
        m = re.match(r"\[(\d\d):(\d\d):(\d\d)\]\s*([^：]+)：(.*)", line)
        if m:
            rows.append((int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)),
                         m.group(5)))
    for it in items:
        best = ""
        for s, txt in rows:
            if s <= it["second"] + 30:
                best = txt
            else:
                break
        it["caption"] = (best[:46] + "…") if len(best) > 46 else (best or "（无语音）")
    return items


def build_illustrated(note_path, items, outdir):
    md = open(note_path, encoding="utf-8").read()
    heads = [h.strip() for h in re.findall(r"^##\s+(.*)$", md, re.M)]
    head_txt = "\n".join(heads)
    times = "\n".join(f"{it['file']} = {it['time']}" for it in items)
    prompt = f"""把每张课件截图分配到最合适的笔记章节。只输出 JSON：
{{"assign":[{{"file":"01_00-00-00.jpg","heading":"一、内容全景"}}]}}

heading 必须逐字取自下列二级标题；每张都要分配，不能遗漏。

标题：
{head_txt}

截图（文件名 = 时刻）：
{times}
"""
    assign = []
    try:
        c = chat([{"role": "user", "content": prompt}], temperature=0.1)
        c = re.sub(r"^```(?:json)?\s*|\s*```$", "", c)
        assign = json.loads(re.search(r"\{.*\}", c, re.S).group(0)).get("assign", [])
    except Exception as e:
        log(f"  !! 章节分配失败（截图将全部放在文末）: {e}")

    by_file = {it["file"]: it for it in items}
    bucket = {}
    for a in assign:
        if a.get("file") in by_file:
            bucket.setdefault(a.get("heading", "").strip(), []).append(a["file"])
    assigned = {f for v in bucket.values() for f in v}
    rest = [it["file"] for it in items if it["file"] not in assigned]

    out, used = [], 0

    def emit(files):
        nonlocal used
        for f in sorted(files, key=lambda x: by_file[x]["second"]):
            it = by_file[f]
            out.append(f"![{it['time']} 课件](幻灯片/{f})")
            out.append(f"*{it['time']}　{it['caption']}*")
            out.append("")
            used += 1

    for line in md.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        out.append(line)
        if m and bucket.get(m.group(1).strip()):
            out.append("")
            emit(bucket[m.group(1).strip()])

    if rest:
        out += ["", "## 附：其余课件截图", ""]
        emit(rest)

    out.insert(1, f"\n> 图文版：正文中穿插 {len(items)} 张课件截图（标注视频时间点，"
                  "对应 `视频\\共享屏幕.mp4`）。\n")
    path = os.path.join(outdir, "笔记_图文版.md")
    open(path, "w", encoding="utf-8").write("\n".join(out))
    log(f"  图文版: 插入 {used} 张截图")
    return path


# ---------- 6. Word / PDF ----------
def export_office(md_path, outdir):
    import md2docx
    docx_path = os.path.join(outdir, "笔记_图文版.docx")
    md2docx.build(md_path, docx_path, outdir)
    log(f"  docx: {os.path.basename(docx_path)}")
    if os.path.exists(NODE) and os.path.exists(LO_CLI):
        pdf = os.path.join(outdir, "笔记_图文版.pdf")
        r = subprocess.run([NODE, LO_CLI, "convert", "--input", docx_path,
                            "--output", pdf], capture_output=True)
        if os.path.exists(pdf):
            log(f"  pdf: {os.path.getsize(pdf) / 1048576:.1f} MB")
        else:
            err = (r.stderr or r.stdout or b"")[:300].decode("utf-8", "replace")
            log(f"  !! pdf 转换失败: {err}")


# ---------- 7. 单文件处理 ----------
def process(path):
    text = open(path, encoding="utf-8", errors="replace").read() if os.path.isfile(path) else path
    url, pwd = parse_input(text)
    if not url:
        log("!! 没找到腾讯会议链接:", path)
        return False
    log(f"开始处理: {url}  密码: {pwd or '（无）'}")

    g = grab(url, pwd)
    if not g["transcript_lines"] and not g["media"]:
        log("!! 没抓到逐字稿也没抓到视频，可能链接失效/需要登录/权限不对")
        return False

    title = (g["meta"].get("subject") or g["meta"].get("title")
             or g["meta"].get("meeting_topic"))
    if not title:
        if os.path.isfile(path):
            title = os.path.splitext(os.path.basename(path))[0]
        else:
            title = re.sub(r"^https?://meeting\.tencent\.com/", "", url).replace("/", "_")
    title = safe_name(title)
    outdir = unique_dir(OUT_DIR, title)
    os.makedirs(outdir, exist_ok=True)
    log(f"输出目录: {outdir}")

    # 视频
    vids = download_videos(g["media"], os.path.join(outdir, "视频"))

    # 逐字稿
    lines = g["transcript_lines"]
    open(os.path.join(outdir, "逐字稿.txt"), "w", encoding="utf-8").write(
        f"{title} · 腾讯会议逐字稿\n覆盖：{g['coverage'][0]} → {g['coverage'][1]}\n"
        + "=" * 60 + "\n\n" + "\n".join(lines) + "\n")
    log(f"  逐字稿: {len(lines)} 段")

    # 笔记
    note_path = gen_note(lines, title, outdir)
    md = open(note_path, encoding="utf-8").read()
    if "视频时间轴" not in md:
        md += "\n\n---\n\n## 视频时间轴\n\n" + gen_timeline(lines) + "\n"
        open(note_path, "w", encoding="utf-8").write(md)

    # 截图 + 图文版
    illustrated = note_path
    screen = next((v for v in vids if "共享屏幕" in v), vids[0] if vids else None)
    if screen:
        items = extract_slides(screen, os.path.join(outdir, "幻灯片"),
                               os.path.join(outdir, "_frames"))
        shutil.rmtree(os.path.join(outdir, "_frames"), ignore_errors=True)
        if items:
            caption_for(items, lines)
            illustrated = build_illustrated(note_path, items, outdir)
    export_office(illustrated, outdir)

    # 元信息
    with open(os.path.join(outdir, "元信息.txt"), "w", encoding="utf-8") as f:
        f.write(f"标题：{title}\n链接：{url}\n")
        f.write(f"逐字稿覆盖：{g['coverage'][0]} → {g['coverage'][1]}\n")
        f.write(f"逐字稿段数：{len(lines)}\n")
        f.write(f"视频文件：{[os.path.basename(v) for v in vids] or '无'}\n")
        f.write(f"笔记模型：{MODEL}\n")
        f.write(f"处理时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        if not vids:
            f.write("注意：未抓到视频直链（可能分享者关闭了播放权限）。\n")
    log("完成:", outdir)
    return outdir


def move_to(path, dest_dir):
    os.makedirs(dest_dir, exist_ok=True)
    base = os.path.basename(path)
    dst = os.path.join(dest_dir, base)
    n = 2
    while os.path.exists(dst):
        root_, ext = os.path.splitext(base)
        dst = os.path.join(dest_dir, f"{root_}_{n}{ext}")
        n += 1
    shutil.move(path, dst)
    return dst


def scan_inputs():
    if not os.path.isdir(IN_DIR):
        return []
    out = []
    for f in sorted(os.listdir(IN_DIR)):
        p = os.path.join(IN_DIR, f)
        if os.path.isfile(p) and os.path.splitext(f)[1].lower() in (".txt", ".url", ".md", ".webloc"):
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", help="投递文件路径或会议链接")
    ap.add_argument("--loop", action="store_true", help="常驻监视输入文件夹")
    ap.add_argument("--interval", type=int, default=60, help="轮询间隔秒")
    args = ap.parse_args()

    for d in (IN_DIR, DONE_DIR, FAIL_DIR, OUT_DIR):
        os.makedirs(d, exist_ok=True)
    sys.path.insert(0, ROOT)

    if args.target:
        if args.target.startswith("http"):
            tmp = os.path.join(IN_DIR, f"手动_{time.strftime('%H%M%S')}.txt")
            open(tmp, "w", encoding="utf-8").write(args.target + "\n")
            move_to(tmp, DONE_DIR)
            ok = process(args.target)
        else:
            ok = process(args.target)
            if ok and os.path.isfile(args.target):
                move_to(args.target, DONE_DIR)
        return 0 if ok else 1

    while True:
        files = scan_inputs()
        if not files:
            if not args.loop:
                log("输入文件夹里没有待处理文件:", IN_DIR)
                return 0
            time.sleep(args.interval)
            continue
        for f in files:
            try:
                ok = process(f)
            except Exception as e:
                log("!! 异常:", type(e).__name__, str(e)[:200])
                ok = False
            move_to(f, DONE_DIR if ok else FAIL_DIR)
        if not args.loop:
            return 0


if __name__ == "__main__":
    sys.exit(main())
