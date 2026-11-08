# =============================================================================
# 老哔拾课 · Windows 一键启动（v1.1.0）
#
# 双击根目录的 start_local.bat 即可。本脚本会按需自动完成：
#   1. 找到可用的 Python（3.10~3.13，优先复用 backend\.venv）
#   2. 创建虚拟环境并安装后端依赖（国内镜像，失败自动回退官方源）
#   3. 解压仓库自带的 ffmpeg（tools\ffmpeg\ffmpeg-*.zip -> tools\ffmpeg\bin）
#   4. 生成 backend\.env（不存在时）
#   5. 安装前端依赖（node_modules 不存在时）
#   6. 启动后端 :8484 与前端 :3017，健康检查通过后自动打开浏览器
#
# 可选参数：
#   -Reinstall     强制重装后端依赖
#   -NoBrowser     不自动打开浏览器
#   -BackendOnly   只启动后端
# =============================================================================
param(
    [switch]$Reinstall,
    [switch]$NoBrowser,
    [switch]$BackendOnly
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$Root      = Split-Path -Parent $PSScriptRoot
$Backend   = Join-Path $Root 'backend'
$Frontend  = Join-Path $Root 'frontend'
$VenvDir   = Join-Path $Backend '.venv'
$VenvPy    = Join-Path $VenvDir 'Scripts\python.exe'
$ReqFile   = Join-Path $Backend 'requirements.txt'
$HashFile  = Join-Path $VenvDir '.requirements.sha256'
$LogDir    = Join-Path $Root 'logs'
$BackendPort  = 8484
$FrontendPort = 3017
$PipMirror = 'https://pypi.tuna.tsinghua.edu.cn/simple'
$NpmMirror = 'https://registry.npmmirror.com'

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $Root

function Write-Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn2($msg){ Write-Host "    [!] $msg" -ForegroundColor Yellow }
function Write-Err($msg)  { Write-Host "    [X] $msg" -ForegroundColor Red }

function Test-Port($port) {
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $iar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
        $ok = $iar.AsyncWaitHandle.WaitOne(400)
        if ($ok) { $client.EndConnect($iar) }
        $client.Close()
        return $ok
    } catch { return $false }
}

function Get-PythonVersion($exe, [string[]]$prefixArgs) {
    try {
        $out = & $exe @prefixArgs -c "import sys;print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) { return ($out | Select-Object -Last 1).Trim() }
    } catch { }
    return $null
}

function Find-CompatiblePython {
    # 返回 @{ Exe = 'py'; Args = @('-3.12') } 这类描述
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in @('3.12', '3.13', '3.11', '3.10')) {
            $ver = Get-PythonVersion 'py' @("-$v")
            if ($ver) { return @{ Exe = 'py'; Args = @("-$v"); Version = $ver } }
        }
    }
    foreach ($cmd in @('python', 'python3')) {
        if (Get-Command $cmd -ErrorAction SilentlyContinue) {
            $ver = Get-PythonVersion $cmd @()
            if ($ver -and $ver -match '^3\.(1[0-3])$') {
                return @{ Exe = $cmd; Args = @(); Version = $ver }
            }
        }
    }
    return $null
}

function New-Venv($pyInfo) {
    Write-Step "创建后端虚拟环境 backend\.venv（Python $($pyInfo.Version)）"
    if ($pyInfo.Exe -eq 'uv') {
        & uv venv --python 3.12 $VenvDir
    } else {
        & $pyInfo.Exe @($pyInfo.Args) -m venv $VenvDir
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPy)) {
        throw "创建虚拟环境失败。请确认 Python 安装完整（含 venv 模块）。"
    }
    Write-Ok "虚拟环境已创建"
}

function Ensure-BackendDeps {
    if (-not (Test-Path $VenvPy)) {
        $pyInfo = Find-CompatiblePython
        if (-not $pyInfo) {
            if (Get-Command uv -ErrorAction SilentlyContinue) {
                $pyInfo = @{ Exe = 'uv'; Args = @(); Version = '3.12 (uv 自动下载)' }
            } else {
                Write-Err "没有找到可用的 Python 3.10~3.13。"
                Write-Host "    请安装 Python 3.12： https://www.python.org/downloads/release/python-3120/" -ForegroundColor Yellow
                Write-Host "    安装时勾选 Add python.exe to PATH，然后重新双击 start_local.bat。" -ForegroundColor Yellow
                Write-Host "    （Python 3.14 目前缺少 ctranslate2 / onnxruntime 的预编译轮子，装不齐依赖。）" -ForegroundColor DarkGray
                throw "缺少 Python 运行时"
            }
        }
        New-Venv $pyInfo
    }

    $needInstall = $Reinstall -or -not (Test-Path $HashFile)
    if (-not $needInstall) {
        $old = (Get-Content $HashFile -ErrorAction SilentlyContinue | Select-Object -First 1)
        $new = (Get-FileHash $ReqFile -Algorithm SHA256).Hash
        if ($old -ne $new) { $needInstall = $true }
    }
    if (-not $needInstall) { Write-Ok "后端依赖已是最新（跳过安装）"; return }

    Write-Step "安装后端依赖（首次约 3~8 分钟，取决于网速）"
    $installed = $false
    foreach ($index in @($PipMirror, $null)) {
        $pipArgs = @('-m', 'pip', 'install', '-q', '--disable-pip-version-check', '-r', $ReqFile)
        if ($index) { $pipArgs += @('-i', $index) }
        Write-Host "    使用源: $(if ($index) { $index } else { 'PyPI 官方' })" -ForegroundColor DarkGray
        & $VenvPy @pipArgs
        if ($LASTEXITCODE -eq 0) { $installed = $true; break }
        Write-Warn2 "该源安装失败，尝试下一个源…"
    }
    if (-not $installed) { throw "后端依赖安装失败，请检查网络或代理设置。" }

    (Get-FileHash $ReqFile -Algorithm SHA256).Hash | Set-Content $HashFile -Encoding ascii
    Write-Ok "后端依赖安装完成"
}

function Ensure-Ffmpeg {
    $bin = Join-Path $Root 'tools\ffmpeg\bin\ffmpeg.exe'
    if (Test-Path $bin) { Write-Ok "ffmpeg 已就绪"; return }
    $zip = Get-ChildItem (Join-Path $Root 'tools\ffmpeg') -Filter 'ffmpeg-*.zip' -ErrorAction SilentlyContinue |
           Select-Object -First 1
    if ($zip) {
        Write-Step "解压自带 ffmpeg"
        $tmp = Join-Path $Root '.cache\ffmpeg-extract'
        Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
        Expand-Archive -Path $zip.FullName -DestinationPath $tmp -Force
        $exe = Get-ChildItem $tmp -Recurse -Filter 'ffmpeg.exe' | Select-Object -First 1
        if ($exe) {
            New-Item -ItemType Directory -Force -Path (Split-Path $bin) | Out-Null
            Copy-Item $exe.FullName $bin -Force
            Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
            Write-Ok "ffmpeg 已解压到 tools\ffmpeg\bin"
        } else {
            Write-Warn2 "压缩包里没有找到 ffmpeg.exe"
        }
    } else {
        Write-Warn2 "未找到 tools\ffmpeg 下的压缩包，截图/转码功能需要自行安装 ffmpeg 并配置 FFMPEG_BIN_PATH"
    }
}

function Ensure-EnvFile {
    $envFile = Join-Path $Backend '.env'
    if (Test-Path $envFile) { Write-Ok "backend\.env 已存在"; return }
    $example = Join-Path $Backend '.env.example'
    if (Test-Path $example) {
        Copy-Item $example $envFile
        Write-Step "已根据 backend\.env.example 生成 backend\.env"
        Write-Warn2 "如需修改端口 / Cookie / 转写模型，编辑 backend\.env 后重启"
    }
}

function Ensure-FrontendDeps {
    if ($BackendOnly) { return }
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Write-Err "没有找到 Node.js。请安装 Node.js 20+： https://nodejs.org/zh-cn/download"
        throw "缺少 Node.js"
    }
    $major = [int]((& node -v).TrimStart('v').Split('.')[0])
    if ($major -lt 20) { throw "Node.js 版本过低（当前 $(node -v)），请升级到 20 或以上。" }

    $modules = Join-Path $Frontend 'node_modules'
    $stamp = Join-Path $Frontend 'node_modules\.package-lock.json'
    if ((Test-Path $modules) -and (Test-Path $stamp)) {
        Write-Ok "前端依赖已安装（跳过）"; return
    }
    Write-Step "安装前端依赖（首次约 1~3 分钟）"
    Push-Location $Frontend
    try {
        $env:npm_config_registry = $NpmMirror
        & npm install --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "国内镜像安装失败，回退官方源重试…"
            $env:npm_config_registry = 'https://registry.npmjs.org'
            & npm install --no-audit --no-fund
        }
        if ($LASTEXITCODE -ne 0) { throw "前端依赖安装失败" }
        Write-Ok "前端依赖安装完成"
    } finally { Pop-Location }
}

function Wait-Http($url, $seconds, $name) {
    Write-Step "等待 $name 就绪（最长 $seconds 秒）"
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $resp = Invoke-RestMethod $url -TimeoutSec 3
            if ($resp -and $resp.code -eq 0) { Write-Ok "$name 已就绪"; return $true }
        } catch { }
        Start-Sleep -Milliseconds 800
    }
    Write-Err "$name 启动超时，请查看 logs\backend.log / logs\frontend.log"
    return $false
}

# ---------------------------------------------------------------------------
Write-Host ''
Write-Host '  ============================================' -ForegroundColor Magenta
Write-Host '   老哔拾课 · 本地启动器  v1.1.0' -ForegroundColor Magenta
Write-Host '  ============================================' -ForegroundColor Magenta

Ensure-BackendDeps
Ensure-Ffmpeg
Ensure-EnvFile
Ensure-FrontendDeps

if (Test-Port $BackendPort) {
    Write-Warn2 "端口 $BackendPort 已有服务在监听，跳过后端启动（如需重启请先运行 stop_local.bat）"
} else {
    Write-Step "启动后端 http://127.0.0.1:$BackendPort"
    Start-Process -FilePath $VenvPy -ArgumentList 'main.py' -WorkingDirectory $Backend `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $LogDir 'backend.log') `
        -RedirectStandardError  (Join-Path $LogDir 'backend.err.log')
}

if (-not (Wait-Http "http://127.0.0.1:$BackendPort/api/sys_check" 120 '后端')) {
    Write-Host "    排查：logs\backend.log / logs\backend.err.log（有旧服务时先运行 stop_local.bat）" -ForegroundColor Yellow
    exit 1
}

if (-not $BackendOnly) {
    if (Test-Port $FrontendPort) {
        Write-Warn2 "端口 $FrontendPort 已有服务在监听，跳过前端启动"
    } else {
        Write-Step "启动前端 http://localhost:$FrontendPort"
        Start-Process -FilePath 'npm.cmd' -ArgumentList 'run', 'dev' -WorkingDirectory $Frontend `
            -WindowStyle Hidden `
            -RedirectStandardOutput (Join-Path $LogDir 'frontend.log') `
            -RedirectStandardError  (Join-Path $LogDir 'frontend.err.log')
    }
    if (-not (Wait-Http "http://127.0.0.1:$FrontendPort/api/sys_check" 90 '前端')) {
        Write-Err "前端没有起来，请检查 logs\frontend.log 或手动在 frontend 目录运行 npm run dev"
        exit 1
    }
    if (-not $NoBrowser) {
        Start-Process "http://localhost:$FrontendPort"
    }
}

Write-Host ''
Write-Host '  启动完成：' -ForegroundColor Green
Write-Host "    前端页面  http://localhost:$FrontendPort" -ForegroundColor White
Write-Host "    后端接口  http://127.0.0.1:$BackendPort/api/sys_health" -ForegroundColor White
Write-Host '  首次使用：设置 → 模型服务 里填 OpenAI 兼容的 Base URL / API Key；' -ForegroundColor DarkGray
Write-Host '           设置 → 音频转写配置 里下载 Whisper 模型。' -ForegroundColor DarkGray
Write-Host '  停止服务：双击 stop_local.bat' -ForegroundColor DarkGray
