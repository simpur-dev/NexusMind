@echo off
REM NexusMind - Neo4j 本地启动脚本（批处理版）
REM 双击运行此文件即可启动 Neo4j

set "NEO4J_DESKTOP=C:\Program Files\Neo4j Desktop 2\Neo4j Desktop 2.exe"
set "NEO4J_DBMS_ROOT=%USERPROFILE%\.Neo4jDesktop\relate-data\dbmss"

if not exist "%NEO4J_DESKTOP%" (
    echo [错误] 未找到 Neo4j Desktop: %NEO4J_DESKTOP%
    pause
    exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (Get-NetTCPConnection -LocalPort 7687 -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if not errorlevel 1 (
    echo ============================================
    echo   Neo4j 似乎已在运行
    echo   Bolt:    bolt://localhost:7687
    echo   Browser: http://localhost:7474
    echo ============================================
    exit /b 0
)

echo ============================================
echo   正在打开 Neo4j Desktop...
echo   Bolt:    bolt://localhost:7687
echo   Browser: http://localhost:7474
if exist "%NEO4J_DBMS_ROOT%\*" (
    echo   状态:    请在 Neo4j Desktop 中启动你的 Local DBMS
) else (
    echo   状态:    未发现本地 DBMS，请先创建并启动一个 Local DBMS
)
echo ============================================
echo.

start "" "%NEO4J_DESKTOP%"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ready=$false; for($i=0;$i -lt 30;$i++){ Start-Sleep -Seconds 2; if (Get-NetTCPConnection -LocalPort 7687 -ErrorAction SilentlyContinue) { $ready=$true; break } }; if($ready){ exit 0 } else { exit 1 }"
if errorlevel 1 (
    echo [提示] Neo4j Desktop 已打开，但 7687 端口尚未监听
    echo [提示] 请在 Neo4j Desktop 中手动启动本地数据库后重试
    pause
    exit /b 1
)

echo [完成] Neo4j 已可连接
