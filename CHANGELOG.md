# 更新记录

## v1.1.2（2026-11-08）· 分组名上限修复

B 站合集批量生成时，分组名是从合集标题自动截出来的（前端 `slice(0, 30)`），
但后端上限只有 20 字——用户根本没手动起名，就先被「分组名最多 20 个字符」拦住，
整批任务直接失败。

### 修复

- 后端分组名上限 20 → **60 字**，创建与重命名共用同一个 `_validate_group_name()`；
  `update_group` 之前完全没做长度校验，现在也补上了。
- 前端自动建组改为按 60 字截断，和下拉里展示的名字一致（原来展示 20、实际提交 30）。
- 自动建组失败不再拖垮整批任务：捕获异常后按「未分组」继续生成，并在进度条提示原因。
- 新建分组 / 重命名输入框加 `maxlength="60"`，创建失败时显示后端真实原因（如重名）。
- 新增 `tests/test_group_name.py` 锁住 60 字上限与空名/裁剪行为。

## v1.1.1（2026-11-08）· 设置页「选不了模型」修复

Ollama 这类本机推理服务不需要 API Key，但旧逻辑把「有 key」当成「可用」的唯一标准，
导致设置页模型下拉为空、首页模型选择显示「未配置」。

### 修复

- `build_openai_client`：`base_url` 指向本机（localhost / 127.0.0.1 / host.docker.internal）时，
  空 key 自动用占位符 `ollama`，不再抛「API Key 未配置」（OpenAI SDK 也不接受空的 `Bearer`）。
- 启动时自动把本机供应商的空 key 补成 `ollama`（`normalize_local_provider_keys`），
  升级已有数据库也能直接生效；`builtin_providers.json` 里 ollama 默认带占位 key。
- 设置页 `loadModels()` 不再因为 `api_key` 为空直接 `return`，而是照常拉取上游模型并把真实错误显示出来。
- 首页供应商筛选接受本机服务（`isLocalProvider`），Ollama 不会再被过滤成「未配置」。
- `Model.provider_id` 类型从 `Integer` 改为 `String`（内置 ollama / UUID 自定义供应商都合法）。

### 设置页其他修复

- 「转写引擎」页原本是写死的静态文案，现在可以选择引擎（fast-whisper / bcut / kuaishou / groq）、
  选择 Whisper 档位、保存配置、查看各档位下载状态并触发下载。
- 「B 站设置」的保存按钮原本没有绑定事件，现在会真正读写本机 Cookie 配置。

## v1.1.0（2026-11-08）· 本地可用性升级

初版是「源码快照」：`start_local.bat` 指向一个本机不存在的 venv，系统 Python 里也没装依赖，
仓库里的 ffmpeg 只是一个没解压的 zip，前端没有 `node_modules`——双击启动必然闪退。
这一版的目标是：**下载解压后双击就能跑起来**，同时修掉一批会直接导致启动/运行失败的问题。

### 启动 / 环境

- 重写 `start_local.bat` + 新增 `scripts/start_local.ps1`：
  自动查找 Python 3.10~3.13 → 创建 `backend/.venv` → 安装依赖（清华镜像，失败回退 PyPI 官方）
  → 解压自带 ffmpeg → 生成 `backend/.env` → 安装前端依赖（npmmirror，失败回退官方）
  → 启动前后端 → 健康检查通过后自动打开浏览器。
- 新增 `stop_local.bat`：按端口停止前后端。
- 依赖标记文件 `.venv/.requirements.sha256`：`requirements.txt` 不变时跳过重复安装。

### 修复（初版会导致「用不了」的问题）

- **后端直接起不来**：`app/services/provider.py` 里 `from kombu import uuid` 依赖 Celery 生态，
  未安装 kombu 时 `ModuleNotFoundError: kombu`。改为标准库 `uuid.uuid4()`。
- `get_data_dir()` 多拼了一层 `data`，音频实际落在 `backend/data/data/`，媒体管理页与
  `/media` 挂载点对不上。已统一到 `backend/data/`。
- 端口默认值混乱：`main.py`/`note.py`/`video_helper.py`/`config.py` 用 8483，
  `start_local.bat`/Vite 代理用 8484，`.env.example` 又是 8483/3015。统一为
  **后端 8484、前端 3017**。
- 截图/转码只调用裸 `ffmpeg` 命令，`FFMPEG_BIN_PATH` 配了也不生效。
  现在 `ffmpeg_helper.get_ffmpeg_bin()` 支持目录或 exe 路径，并在启动时写进 `PATH`。
- 笔记库分组标题 `button` 套 `button`（非法 HTML，点「下载整组」会同时折叠分组）。
- 3 个 YouTube 用例写死 `/tmp`，Windows 上必然 `PermissionError`。
- 两处正则字符串缺少 `r` 前缀，每次启动刷 `SyntaxWarning: invalid escape sequence`。
- Windows 控制台中文日志乱码：启动器切 UTF-8（`chcp 65001` + PowerShell 输出编码）。

### 新增

- `BILIBILI_COOKIES_FROM_BROWSER=edge|chrome|firefox`：直接复用本机浏览器 B 站登录态，
  不用手动复制 SESSDATA。优先级：手动 Cookie > 浏览器 Cookie。
- `/api/sys_health` 之外的启动期 ffmpeg 自检日志（缺 ffmpeg 时明确告警，而不是转到一半才失败）。

### 依赖升级

| 组件 | 初版 | v1.1.0 |
|---|---|---|
| FastAPI | 0.116.2 | 0.162.2 |
| Uvicorn | 0.34.0 | 0.54.0 |
| SQLAlchemy | 2.0.41 | 2.1.8 |
| Pydantic | 2.11.2 | 2.14.3 |
| openai | 1.70.0 | 3.46.0 |
| yt-dlp | 2026.7.4 | 2026.10.26 |
| faster-whisper | 1.1.1 | 1.2.1 |
| CTranslate2 | 4.6.0 | 4.8.5 |
| PyAV (`av`) | 14.2.0 | **16.1.0（锁定，见下）** |
| ChromaDB | 0.5.x | 1.5.9 |
| HuggingFace Hub | 0.30.2 | 2.4.0 |

PyAV 必须锁 `16.1.0`：faster-whisper 1.2.1 调用 `av.open(..., metadata_errors="ignore")`，
而 av 17+ 删除了该参数，装 19.x 会在每次转写时报
`open() got an unexpected keyword argument 'metadata_errors'`（已实测）。

`requirements.txt` 从 129 行全量 freeze 精简为约 20 个直接依赖，去掉了运行期用不到的
celery / redis / kombu / weasyprint / pyinstaller / modelscope 等；Python 支持范围明确为
3.10~3.13（3.14 目前缺少 ctranslate2 / onnxruntime 轮子，装不齐）。

### 已知限制

- 本仓库主分支在初版快照基础上维护；未接入上游 BiliNote 的后续功能。
- AI 问答的向量索引使用 ChromaDB 默认本地嵌入模型，首次建索引需要联网下载 ~80MB 模型
  （缓存到 `%USERPROFILE%\.cache\chroma`），下载失败只影响 AI 问答，不影响笔记生成。
- PDF 导出模块（`app/utils/export.py`）在初版就没有接入路由，本版未启用。
