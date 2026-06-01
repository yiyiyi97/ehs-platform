@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo   EHS 日报后台服务 - 打包工具
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

REM 安装依赖
echo [1/3] 安装打包依赖...
pip install pyinstaller pystray pillow -i https://pypi.tuna.tsinghua.edu.cn/simple

REM 打包
echo [2/3] 打包 exe...
pyinstaller --onefile --noconsole --name EHS日报服务 ehs_daemon.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo [3/3] 复制文件...
if not exist "dist\ehs_shift_report.py" (
    copy ehs_shift_report.py dist\
)

echo.
echo ==========================================
echo   打包完成！
echo ==========================================
echo.
echo 文件位置:
echo   dist\EHS日报服务.exe   ^<-- 双击运行
echo   dist\ehs_shift_report.py  ^<-- 日报脚本（需同目录）
echo.
echo 部署步骤:
echo   1. 把 dist 文件夹复制到目标电脑
echo   2. 修改 dist\ehs_shift_report.py 里的配置
echo   3. 双击 EHS日报服务.exe
echo   4. 系统托盘出现蓝色图标即表示运行中
echo.
pause
