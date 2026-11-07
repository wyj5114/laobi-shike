# 老哔拾课

> 老哔拾课，你值得拥有。

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

- Python 3.11+
- Node.js 20+
- FFmpeg（仓库已附带 Windows 版：`tools/ffmpeg/bin/ffmpeg.exe`）
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

- `tools/ffmpeg/bin/ffmpeg.exe`：Windows x64 FFmpeg，可直接使用。
- `tools/README.md`：FFmpeg 配置、torch GPU 安装、GitHub LFS/Releases 说明。
- torch CUDA wheel 已放在 `tools/torch/`（约 3.05 GB），不能直接提交普通 GitHub 仓库；请作为 Release 资产上传或使用 Git LFS，详见 `tools/README.md`。

## 启动

### Windows

```bat
start_local.bat
```

默认后端 `http://127.0.0.1:8484`，前端 `http://localhost:3017`。

### 手动启动

```bash
# 后端
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py

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

复制 `.env.example` 为 `.env` 按需修改。常用项：

- `WHISPER_MODEL_SIZE`：`tiny` / `base` / `small` / `medium` / `large-v3`
- `YDL_CONCURRENT_FRAGMENTS`：下载分片并发
- `VIDEO_MAX_HEIGHT`：截图场景视频最高分辨率
- `NOTE_OUTPUT_DIR`：笔记结果目录
- `TASK_MAX_WORKERS`：全局任务并发，默认 3

## 说明


- 初版聚焦 B 站 Web 端；浏览器扩展与桌面端在后续版本。
- 请遵守 B 站服务条款与版权规定，仅用于个人学习。

---

## 腾讯会议回放解析（新增）

把腾讯会议的**回放链接 + 密码**直接变成一套能复习的资料：带时间戳逐字稿、分节笔记、
插了课件截图的图文版 Word / PDF，并把回放视频顺手下载下来。

### 用法（三种都行）

1. **粘贴链接**：双击 `解析腾讯会议回放.bat` → 粘链接回车 → 粘密码回车（没密码直接回车）
2. **投递箱**：把链接和密码写进 txt 丢到 `腾讯会议解析\输入\`，双击 `解析腾讯会议回放.bat`
3. **常驻监视**：双击 `一键监视全部.bat`，之后往输入箱丢 txt 自动处理（`停止监视全部.bat` 停止）

txt 格式（同一行或分两行都认，`密码：` / `口令：` / `pwd:` 都行）：

```
https://meeting.tencent.com/crm/2MMQAG4Z6c
密码：1OWA
```

### 输出

```
腾讯会议解析\输出\<会议名>\
  笔记.md            分节笔记（KaTeX 公式）
  笔记_图文版.md     正文插入了课件截图
  笔记_图文版.docx   Word
  笔记_图文版.pdf    PDF
  逐字稿.txt         带时间戳逐字稿
  幻灯片\            自动挑出来的课件关键帧
  视频\              共享屏幕.mp4 / 发言人.mp4
  元信息.txt
```

### 环境依赖

- Python：`requests`、`numpy`、`Pillow`、`python-docx`、`playwright`
- `tools/ffmpeg/bin/ffmpeg.exe`（抽帧、切音频）
- OpenAI 兼容的模型接口：环境变量 `SHIKE_PROXY` / `SHIKE_MODEL` / `SHIKE_PROXY_KEY`，
  或同目录放一个 `_local_key.txt`（不入库）
- LibreOffice（导出 PDF，可选）
- 首次运行会用 Playwright 打开 Edge 让你登录腾讯会议，登录态存在 `_edge_profile/`（不入库）

### 实现要点

- 逐字稿走内部接口 `wemeet-cloudrecording-webapi/v1/minutes/detail`，接口是**分页**的，
  靠滚动逐字稿面板触发加载，再按 `pid` 合并；文字在 `sentences[].words[].text`
- 笔记分**两遍**生成：逐字稿分段精读 → 合并成稿（一遍生成会漏掉「例题与解法」章节）
- 课件截图：每 15 秒抽一帧，按画面差异去重，由模型判断归属章节后插进正文
- 部分本地代理会**丢弃 system 消息**，所以指令统一折进 user 消息（见 `_fold_system`）
