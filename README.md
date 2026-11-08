# 老哔拾课

> 老哔拾课，你值得拥有。

**当前版本：v1.1.0（本地可用性升级，2026-11-08）**——修复了初版「下载后双击启动必失败」的一整套问题，
并升级依赖。详细改动见 [CHANGELOG.md](CHANGELOG.md)。

## 哔站拾课 · 初版（完整功能）

把 B 站课程视频，变成可复习、可检索、可对话的笔记。

这是「哔站拾课」的初版源码快照，包含 Web 前端与 FastAPI 后端，可直接作为 GitHub 仓库初始版本。

## 功能

- 粘贴 B 站视频链接，生成结构化课程笔记
- **B 站合集 / 多 P 自动识别**：识别「149 P」、合集、UP 主系列
- **批量生成**：全选 / 只选未生成 / 选范围，一键加入队列
- **批量并发 1 / 2 / 3** 可选
- 本地 faster-whisper 转写（支持 CUDA，失败自动回退 CPU）
- 转写原话「整理」：去除口头废话，保留时间戳
- 笔记 / 整理 / 思维导图 / AI 问答四个阅读 Tab
- AI 问答：RAG 检索、SSE 流式输出、引用来源可跳转
- 多模型供应商管理（OpenAI 兼容接口）
- 笔记分组、改名、移动、导出 Markdown
- **分组一键下载全部 Markdown（ZIP）**
- 笔记库 / 任务页：每页 50 条，支持上一页 / 下一页
- 任务页：按分组折叠，可一键全部收起；进行中 → 未开始 → 已完成
- 视频区：查看 / 清理音频、视频、截图缓存
- 五套主题：Cobalt、国风、Claude 暖纸、天空蓝、宫崎骏风·森系
- 顶部搜索（⌘K / Ctrl+K）直达搜索页
- 笔记正文：表格样式、章节大纲、KaTeX 公式渲染
- 任务页真实阶段日志

## 技术栈

- 前端：Vue 3 + Vite + TypeScript + Pinia + Tailwind CSS 4
- 后端：Python 3.11 + FastAPI + SQLite + SQLAlchemy
- 下载：yt-dlp
- 转写：faster-whisper / CTranslate2
- 向量检索：ChromaDB
- 公式：KaTeX；思维导图：markmap

## 目录

```
backend/
  app/            FastAPI 应用
  skills/         笔记生成 Skill
  tests/          pytest
  main.py         后端入口
frontend/
  src/            Vue 前端
start_local.bat   Windows 一键启动
.env.example      环境变量示例
```

## 环境要求

- Python **3.10 ~ 3.13**（推荐 3.12；3.14 缺少 ctranslate2 / onnxruntime 轮子，装不齐依赖）
- Node.js 20+
- FFmpeg（仓库已附带 Windows 版压缩包：`tools/ffmpeg/ffmpeg-9.0.1-essentials-win64.zip`，
  启动器会自动解压到 `tools/ffmpeg/bin/ffmpeg.exe`）
- GPU 转写可选：torch 2.7.1 + CUDA 12.8（安装方法见 `tools/README.md`）

## 硬件与转写方案建议

转写速度主要取决于是否有 GPU 加速。CPU 也能跑，但通常慢 3~5 倍。以下是 `base` 模型、仅计算「语音转写」的实测/估算，不含音频下载和 AI 生成笔记：

| 设备 / 方案 | 30 分钟音频 | 60 分钟音频 | 建议 |
|---|---|---|---|
| **RTX 5060 · CUDA base** | 约 **2~2.5 分钟** | 约 4~5 分钟 | 游戏本首选；NVIDIA 独显 + CUDA 12.8 |
| **Mac M 系列 · MLX base** | 约 **2.5~4 分钟** | 约 5~8 分钟 | Apple Silicon 首选；`mlx-whisper` |
| Mac M 系列 · CPU int8 base | 约 4~7 分钟 | 约 8~14 分钟 | 没装 MLX 时的回退方案 |
| Intel Mac · CPU int8 base | 约 8~15 分钟 | 约 16~30 分钟 | 无 CUDA，只能用 CPU |

### 游戏本 / Windows NVIDIA

建议直接用 GPU，不要用 CPU 硬跑：

- 使用 NVIDIA 独显，插电并开启「独显直连 / 高性能模式」
- 安装 CUDA 12.8 版 torch（本项目验证环境为 `torch 2.7.1+cu128`）
- 转写器选择 `fast-whisper`，模型先用 `base`
- 8 GB 显存建议批量并发 **1~2**，不要直接上 3

```powershell
python -m pip install torch==2.7.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

### Mac

**Apple Silicon（M1/M2/M3/M4）建议用 MLX，不要用 CPU 版**：

```bash
python -m pip install mlx-whisper
```

然后在「设置 → 转写引擎」选择 `mlx-whisper`，模型用 `base`。MLX 走 Apple Metal，速度明显快于 CPU。

**Intel Mac** 没有 CUDA，也没有 MLX，只能 CPU；建议用 `base` 或 `tiny`，30 分钟音频大约 8~15 分钟。

### 模型选择

- `tiny`：最快，适合快速过一遍
- `base`：**默认推荐**，速度和识别质量平衡
- `small`：质量更好，但 CPU 上明显更慢
- `medium` / `large-v3`：建议只在 GPU 上使用

> 以上只是转写时间；完整任务还要加上 B 站音频下载和 AI 生成笔记的时间。
## 工具

- `tools/ffmpeg/bin/ffmpeg.exe`：Windows x64 FFmpeg，启动器首次运行会自动从压缩包解压到这里。
- `tools/README.md`：FFmpeg 配置、torch GPU 安装、GitHub LFS/Releases 说明。
- torch CUDA wheel 已放在 `tools/torch/`（约 3.05 GB），不能直接提交普通 GitHub 仓库；请作为 Release 资产上传或使用 Git LFS，详见 `tools/README.md`。

## 启动

### Windows（推荐：一键）

```bat
start_local.bat
```

首次运行会自动完成：创建 `backend\.venv` → 安装后端依赖（清华镜像，失败回退官方源）→
解压自带 ffmpeg → 生成 `backend\.env` → 安装前端依赖（npmmirror，失败回退官方源）→
启动后端 `:8484` 和前端 `:3017` → 健康检查通过后打开浏览器。**不需要手动装任何 Python 包。**

常用参数（直接跟在命令后面）：

```bat
start_local.bat -NoBrowser     :: 不自动打开浏览器
start_local.bat -Reinstall    :: 强制重装后端依赖
start_local.bat -BackendOnly  :: 只启动后端
```

停止服务：双击 `stop_local.bat`（按端口结束 8484 / 3017 的进程）。

日志：`logs\backend.log`、`logs\frontend.log`（异常另见 `*.err.log`），以及 `backend\logs\app.log`。

### 手动启动

```powershell
# 后端（Windows PowerShell）
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py

# 前端（另开终端）
cd frontend
npm install
npm run dev
```

首次使用：

1. 打开 `设置 → 模型服务`，添加 OpenAI 兼容供应商、Base URL、API Key
2. 在 `设置 → 转写引擎` 下载 Whisper 模型
3. 回首页粘贴 B 站视频链接生成笔记

API Key 只保存在本机 SQLite 中，不会写入代码或仓库。

## 配置

本地运行改 `backend\.env`（首次启动会自动生成）；Docker 部署改根目录 `.env`。常用项：

- `TRANSCRIBER_TYPE`：`fast-whisper` / `bcut` / `kuaishou` / `groq`（Mac 可用 `mlx-whisper`）
- `WHISPER_MODEL_SIZE`：`tiny` / `base` / `small` / `medium` / `large-v3`
- `BILIBILI_COOKIES_FROM_BROWSER`：`edge` / `chrome` / `firefox`，直接复用浏览器 B 站登录态
- `YDL_CONCURRENT_FRAGMENTS`：下载分片并发
- `VIDEO_MAX_HEIGHT`：截图场景视频最高分辨率
- `NOTE_OUTPUT_DIR`：笔记结果目录
- `TASK_MAX_WORKERS`：全局任务并发，默认 3

## 常见问题

**双击 `start_local.bat` 闪退 / 报「没有找到可用的 Python 3.10~3.13」**
装一个 Python 3.12（安装时勾选 Add to PATH），再重新双击。不要用 Python 3.14：
ctranslate2、onnxruntime 目前没有 3.14 的预编译轮子。

**后端起来了但页面打不开 / 一直转圈**
先看 `logs\frontend.log`；再确认 3017 端口没被占用（`start_local.bat` 检测到已占用会跳过启动）。
停掉旧进程用 `stop_local.bat`。

**设置里模型下拉是空的 / 首页模型显示「未配置」**
本机 Ollama 不需要 API Key，v1.1.1 之前会被误判成「未配置」。升级后：确认 `ollama list` 有模型，
在「设置 → 模型服务」左栏点 **ollama**，右侧「模型」区域会列出本机模型，选中后点「添加模型」；
首页顶部就能选到它。若仍为空，点一次「刷新」或重启 `start_local.bat` 让后端补全占位 Key。

**分组名报「最多 20 个字符」/ 合集自动建组失败**
v1.1.2 起上限已放宽到 **60 字**。B 站合集批量生成时会用合集标题自动建分组，旧版本按 30 字截、
后端却只允许 20 字，所以「还没自己起名就被拒」。升级后自动建组按 60 字截断；万一建组仍失败，
会按「未分组」继续生成，不再让整批任务失败。

**生成笔记时报 ffmpeg 未安装**
`tools\ffmpeg\bin\ffmpeg.exe` 应该由启动器自动解压。若手动运行后端，请在 `backend\.env`
里把 `FFMPEG_BIN_PATH` 指向 ffmpeg 所在目录（或 exe 完整路径）。

**B 站视频下载失败 / 只有 480P**
B 站对未登录请求限制清晰度，部分视频需要登录态才给 1080P 和高码率音频。两种做法：
在「设置 → 下载 Cookie」粘贴浏览器 Cookie；或在 `backend\.env` 设置
`BILIBILI_COOKIES_FROM_BROWSER=edge`（读本机 Edge 登录态）。

**AI 问答报向量索引失败**
ChromaDB 默认嵌入模型首次使用要联网下载（约 80MB）。下载失败只影响 AI 问答，
笔记生成不受影响；可配置代理后重试。

**中文日志乱码**
用 `start_local.bat` 启动（已切 UTF-8）；手动启动时先执行 `chcp 65001` 并设置 `PYTHONUTF8=1`。

## 说明

- 初版聚焦 B 站 Web 端；浏览器扩展与桌面端在后续版本。
- 请遵守 B 站服务条款与版权规定，仅用于个人学习。
- v1.1.0 是本地可用性升级：修启动/路径/编码/端口问题并升级依赖，不改变笔记生成流程。





