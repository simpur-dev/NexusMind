# NexusMind - Neo4j 本地启动脚本
# 用法：在项目根目录运行 `.\scripts\start-neo4j.ps1`

$ErrorActionPreference = "Stop"

$desktopExe = "C:\Program Files\Neo4j Desktop 2\Neo4j Desktop 2.exe"
$desktopDbmsRoot = Join-Path $env:USERPROFILE ".Neo4jDesktop\relate-data\dbmss"

if (-not (Test-Path $desktopExe)) {
    Write-Host "[错误] 未找到 Neo4j Desktop: $desktopExe" -ForegroundColor Red
    Write-Host "       请确认 Neo4j Desktop 已安装" -ForegroundColor Red
    exit 1
}

$existing = Get-NetTCPConnection -LocalPort 7687 -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[提示] 端口 7687 已被占用，Neo4j 可能已在运行" -ForegroundColor Yellow
    Write-Host "       Bolt:    bolt://localhost:7687" -ForegroundColor Gray
    Write-Host "       Browser: http://localhost:7474" -ForegroundColor Gray
    exit 0
}

$dbmss = @()
if (Test-Path $desktopDbmsRoot) {
    $dbmss = @(Get-ChildItem -Path $desktopDbmsRoot -Directory -ErrorAction SilentlyContinue)
}

Write-Host "正在打开 Neo4j Desktop..." -ForegroundColor Cyan
Write-Host "  Desktop: $desktopExe" -ForegroundColor Gray
Write-Host "  Bolt:    bolt://localhost:7687" -ForegroundColor Gray
Write-Host "  Browser: http://localhost:7474" -ForegroundColor Gray
if ($dbmss.Count -eq 0) {
    Write-Host "  状态:    未发现本地 DBMS，请先在 Neo4j Desktop 中创建并启动一个 Local DBMS" -ForegroundColor Yellow
}
else {
    Write-Host "  状态:    请在 Neo4j Desktop 中启动你的 Local DBMS" -ForegroundColor Yellow
}
Write-Host ""

Start-Process -FilePath $desktopExe

for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 2
    $existing = Get-NetTCPConnection -LocalPort 7687 -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "[完成] Neo4j 已可连接" -ForegroundColor Green
        Write-Host "       Bolt:    bolt://localhost:7687" -ForegroundColor Gray
        Write-Host "       Browser: http://localhost:7474" -ForegroundColor Gray
        exit 0
    }
}

Write-Host "[提示] Neo4j Desktop 已打开，但 7687 端口尚未监听" -ForegroundColor Yellow
Write-Host "       请在 Neo4j Desktop 中手动启动本地数据库后重试" -ForegroundColor Yellow
exit 1
