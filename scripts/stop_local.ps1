# 老哔拾课 · 停止本地服务（端口 8484 / 3017）
$ErrorActionPreference = 'SilentlyContinue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

$ports = @(8484, 3017)
$found = $false

foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $conns) {
        $found = $true
        $procId = $conn.OwningProcess
        $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
        $name = if ($proc) { $proc.ProcessName } else { 'unknown' }
        Write-Host "停止端口 $port 上的进程 PID=$procId ($name)" -ForegroundColor Yellow
        # 先杀子进程再杀父进程，避免 npm 退出后 node 还占着端口
        Get-CimInstance Win32_Process -Filter "ParentProcessId=$procId" -ErrorAction SilentlyContinue |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
    }
}

if ($found) {
    Write-Host '已停止 老哔拾课 的后端 / 前端进程。' -ForegroundColor Green
} else {
    Write-Host '没有发现监听 8484 / 3017 的进程（可能已经停了）。' -ForegroundColor DarkGray
}
Start-Sleep -Seconds 1
