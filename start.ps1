# 一键启动行测智能学习系统
$ErrorActionPreference = "SilentlyContinue"
$root = $PSScriptRoot

Write-Host "=== 启动行测智能学习系统 ==="

# 端口占用检查
if (Get-NetTCPConnection -LocalPort 8000 -State Listen) { Write-Host "[跳过] 后端 8000 已在运行" ; $beRunning = $true }
if (Get-NetTCPConnection -LocalPort 5173 -State Listen) { Write-Host "[跳过] 前端 5173 已在运行" ; $feRunning = $true }

# 启动后端
if (-not $beRunning) {
    $be = Start-Process python -ArgumentList "-m","uvicorn","main:app","--host","127.0.0.1","--port","8000" -WorkingDirectory "$root\backend" -WindowStyle Minimized -PassThru
    Write-Host "后端启动中 PID=$($be.Id) -> http://127.0.0.1:8000"
}

# 启动前端
if (-not $feRunning) {
    $fe = Start-Process "C:\Program Files\nodejs\node.exe" -ArgumentList "$root\frontend\node_modules\vite\bin\vite.js","--host","127.0.0.1","--port","5173" -WorkingDirectory "$root\frontend" -WindowStyle Minimized -PassThru
    Write-Host "前端启动中 PID=$($fe.Id) -> http://127.0.0.1:5173"
}

# 记录 PID
$pids = @()
if ($be) { $pids += $be.Id }
if ($fe) { $pids += $fe.Id }
if ($pids.Count) { $pids -join " " | Set-Content "$root\.pids" -Encoding UTF8 }

# 等待就绪
Write-Host "等待服务就绪..."
Start-Sleep -Seconds 7

# 健康检查
try { $h = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -TimeoutSec 5; Write-Host "后端健康: $($h.Content)" } catch { Write-Host "后端未就绪: $($_.Exception.Message)" }
try { $f = Invoke-WebRequest -Uri "http://127.0.0.1:5173/" -UseBasicParsing -TimeoutSec 5; Write-Host "前端就绪: $($f.StatusCode)" } catch { Write-Host "前端未就绪: $($_.Exception.Message)" }

# 打开浏览器
Start-Process "http://127.0.0.1:5173"
Write-Host "`n已打开浏览器。停止服务请运行: .\stop.ps1"