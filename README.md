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
BillNote_frontend_vue/
  src/            Vue 前端
start_local.bat   Windows 一键启动
.env.example      环境变量示例
```

## 环境要求

- Python 3.11+
- Node.js 20+
- FFmpeg（仓库已附带 Windows 版：`tools/ffmpeg/bin/ffmpeg.exe`）
- GPU 转写可选：torch 2.7.1 + CUDA 12.8（安装方法见 `tools/README.md`）

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
cd BillNote_frontend_vue
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





