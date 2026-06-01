@echo off
chcp 65001 >nul
title EHS 本地日报服务
cd /d "%~dp0"

echo ==========================================
echo   EHS 本地日报服务启动器
echo ==========================================
echo.
echo 本服务用于供网页按钮调用，执行本地日报推送
echo 服务地址: http://127.0.0.1:8765
echo.
echo 按 Ctrl+C 停止服务
echo ==========================================
echo.

python ehs_local_service.py

pause