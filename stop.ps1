# 停止行测智能学习系统服务
$root = $PSScriptRoot
$pidFile = "$root\.pids"
if (Test-Path $pidFile) {
    $pids = (Get-Content $pidFile -Raw) -split '\s+' | Where-Object { $_ -match '^\d+$' }
    foreach ($p in $pids) {
        Stop-Process -Id ([int]$p) -Force -ErrorAction SilentlyContinue
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "已停止服务 (PID: $($pids -join ', '))"
} else {
    Write-Host "未找到 PID 记录(.pids)，可手动关闭后端(python)与前端(node)进程"
}