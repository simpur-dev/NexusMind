@echo off
REM NexusMind - Neo4j 本地启动脚本（批处理版）
REM 双击运行此文件即可启动 Neo4j

set NEO4J_HOME=E:\NexusMind\neo4j\neo4j-enterprise-5.24.0
set NEO4J_ACCEPT_LICENSE_AGREEMENT=yes

if not exist "%NEO4J_HOME%\bin\neo4j.bat" (
    echo [错误] 未找到 Neo4j: %NEO4J_HOME%
    pause
    exit /b 1
)

echo ============================================
echo   Neo4j 启动中...
echo   Bolt:    bolt://localhost:7687
echo   Browser: http://localhost:7474
echo   账号:    neo4j / neo4jneo4j
echo   停止:    按 Ctrl+C
echo ============================================
echo.

call "%NEO4J_HOME%\bin\neo4j.bat" console
