# NexusMind - Neo4j 本地启动脚本
# 用法：在项目根目录运行 `.\scripts\start-neo4j.ps1`

$ErrorActionPreference = "Stop"

$neo4jHome = "E:\NexusMind\neo4j\neo4j-enterprise-5.24.0"

if (-not (Test-Path "$neo4jHome\bin\neo4j.bat")) {
    Write-Host "[错误] 未找到 Neo4j 安装目录: $neo4jHome" -ForegroundColor Red
    Write-Host "       请确认 neo4j 文件夹未被移动或删除" -ForegroundColor Red
    exit 1
}

# 检查端口 7687 是否已被占用（Neo4j 已在运行）
$existing = Get-NetTCPConnection -LocalPort 7687 -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "[提示] 端口 7687 已被占用，Neo4j 可能已在运行" -ForegroundColor Yellow
    Write-Host "       Bolt:    bolt://localhost:7687" -ForegroundColor Gray
    Write-Host "       Browser: http://localhost:7474" -ForegroundColor Gray
    exit 0
}

$env:NEO4J_ACCEPT_LICENSE_AGREEMENT = "yes"

Write-Host "正在启动 Neo4j (enterprise 5.24.0)..." -ForegroundColor Cyan
Write-Host "  Home:    $neo4jHome" -ForegroundColor Gray
Write-Host "  Bolt:    bolt://localhost:7687" -ForegroundColor Gray
Write-Host "  Browser: http://localhost:7474" -ForegroundColor Gray
Write-Host "  账号:    neo4j / neo4jneo4j" -ForegroundColor Gray
Write-Host "  停止:    在此窗口按 Ctrl+C" -ForegroundColor Gray
Write-Host ""

& "$neo4jHome\bin\neo4j.bat" console
