# 工具与运行环境

本目录放本地工具安装包。大体积二进制不建议直接进入 GitHub 源码历史。

## FFmpeg

已附带 Windows x64 安装包：

```text
tools/ffmpeg/ffmpeg-9.0.1-essentials-win64.zip
```

解压后得到 `ffmpeg.exe`。也可以直接使用已解压版本：

```text
tools/ffmpeg/bin/ffmpeg.exe
```

### 使用方式

临时加入当前终端 PATH：

```powershell
$env:PATH = "$PWD\tools\ffmpeg\bin;$env:PATH"
ffmpeg -version
```

或设置后端环境变量：

```powershell
$env:FFMPEG_BIN_PATH = "$PWD\tools\ffmpeg\bin\ffmpeg.exe"
```

### 用途

- 从视频中提取音频（m4a/wav）
- 截图、拼图、剪辑
- 转写前的音频格式转换

## Torch GPU（CUDA 12.8）

已从本机 pip 缓存提取官方安装包：

```text
tools/torch/torch-2.7.1+cu128-cp312-cp312-win_amd64.whl
```

- 版本：`torch 2.7.1+cu128`
- Python：`cp312`（Python 3.12 x64）
- 大小：约 **3.05 GB**

### 安装

```powershell
python -m pip install "tools\torch\torch-2.7.1+cu128-cp312-cp312-win_amd64.whl"
```

如果还需要 torchvision / torchaudio，建议使用官方索引安装匹配版本：

```powershell
python -m pip install torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
```

验证：

```powershell
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

应输出类似：

```text
2.7.1+cu128 12.8 True
```

### GitHub 注意

GitHub 普通仓库单文件上限 **100 MB**，这个 wheel 有 **3.05 GB**，不能直接 `git add` 到普通仓库。

选择其中一种：

1. **GitHub Releases**（推荐）：把 `.whl` 作为 Release Asset 上传。
2. **Git LFS**：安装 Git LFS 后跟踪大文件：

```bash
git lfs install
git lfs track "tools/torch/*.whl"
git add .gitattributes
```

> GitHub 对 Git LFS 有单独的存储/带宽额度，公开仓库也有限制，发布前先确认。

## 说明

- `ffmpeg` 来自 Gyan.FFmpeg Essentials Build，仅用于本地音频处理。
- 其他系统请安装对应平台的 ffmpeg，并设置 `FFMPEG_BIN_PATH`。
- 不要把 `models/`、`note_results/`、`vector_db/`、`.env` 或 API Key 提交到仓库。
