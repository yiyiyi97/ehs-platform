#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EHS 日报后台服务（带系统托盘）
自动在每天 08:30（夜班日报）和 20:30（白班日报）执行推送

打包成 exe（无 Python 环境也能运行）:
    pip install pyinstaller pystray pillow
    pyinstaller --onefile --noconsole ehs_daemon.py

运行:
    双击 dist\ehs_daemon.exe
    托盘出现蓝色图标，右键可手动触发或退出
    日志保存在同目录 ehs_daemon.log
"""

import os
import sys
import time
import subprocess
import threading
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════
#  路径配置
# ═══════════════════════════════════════════════════════════════

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_SCRIPT = os.path.join(BASE_DIR, "ehs_shift_report.py")
LOG_FILE = os.path.join(BASE_DIR, "ehs_daemon.log")

# ═══════════════════════════════════════════════════════════════
#  日志
# ═══════════════════════════════════════════════════════════════

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
#  定时逻辑
# ═══════════════════════════════════════════════════════════════

def get_next_shift_time(now=None):
    """
    计算下一个执行时间点和对应班次。
    08:30 → 发夜班日报（覆盖昨晚20:30~今早08:30）
    20:30 → 发白班日报（覆盖今早08:30~今晚20:30）
    """
    if now is None:
        now = datetime.now()

    today_0830 = now.replace(hour=8, minute=30, second=0, microsecond=0)
    today_2030 = now.replace(hour=20, minute=30, second=0, microsecond=0)

    if now > today_2030:
        # 已过今晚 20:30，等明天 08:30（夜班日报）
        return today_0830 + timedelta(days=1), "night"
    elif now > today_0830:
        # 已过今早 08:30，等今晚 20:30（白班日报）
        return today_2030, "day"
    else:
        # 今早 08:30 之前，等今早 08:30（夜班日报）
        return today_0830, "night"


def run_report(shift_type):
    """调用 ehs_shift_report.py 执行推送"""
    log(f"开始执行 {shift_type} 日报推送...")
    if not os.path.exists(REPORT_SCRIPT):
        log(f"错误：找不到日报脚本 {REPORT_SCRIPT}")
        return False

    try:
        cmd = [sys.executable, REPORT_SCRIPT, "--shift", shift_type]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace"
        )
        for line in result.stdout.splitlines():
            log(f"[OUT] {line}")
        if result.stderr:
            for line in result.stderr.splitlines():
                log(f"[ERR] {line}")
        ok = result.returncode == 0 and "推送成功" in result.stdout
        log(f"结果: {'成功' if ok else '失败'} (returncode={result.returncode})")
        return ok
    except Exception as e:
        log(f"执行异常: {e}")
        return False


# ═══════════════════════════════════════════════════════════════
#  托盘图标（需要 pystray + Pillow）
# ═══════════════════════════════════════════════════════════════

try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False
    log("[WARN] 未安装 pystray / Pillow，将以无托盘模式运行")


def create_icon_image(color=(0, 120, 212)):
    """生成一个简单的方形图标"""
    width = 64
    height = 64
    image = Image.new("RGB", (width, height), color)
    dc = ImageDraw.Draw(image)
    # 画一个白色的 "E"
    dc.rectangle([18, 14, 46, 18], fill="white")
    dc.rectangle([18, 14, 22, 50], fill="white")
    dc.rectangle([18, 30, 38, 34], fill="white")
    dc.rectangle([18, 46, 46, 50], fill="white")
    return image


def tray_menu():
    """托盘右键菜单"""
    return pystray.Menu(
        pystray.MenuItem("手动推送 · 白班日报", lambda icon, item: threading.Thread(target=run_report, args=("day",), daemon=True).start()),
        pystray.MenuItem("手动推送 · 夜班日报", lambda icon, item: threading.Thread(target=run_report, args=("night",), daemon=True).start()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("查看日志", lambda icon, item: os.startfile(LOG_FILE)),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", lambda icon, item: icon.stop()),
    )


def run_tray():
    """启动托盘图标"""
    if not HAS_TRAY:
        return None
    icon = pystray.Icon("EHS日报")
    icon.icon = create_icon_image()
    icon.title = "EHS 日报服务运行中"
    icon.menu = tray_menu()
    return icon


# ═══════════════════════════════════════════════════════════════
#  主循环
# ═══════════════════════════════════════════════════════════════

def scheduler_loop():
    """定时器线程：睡眠到下一个执行点，然后推送"""
    while True:
        next_time, shift = get_next_shift_time()
        now = datetime.now()
        wait_seconds = (next_time - now).total_seconds()

        log("=" * 40)
        log(f"下次执行: {next_time.strftime('%Y-%m-%d %H:%M')} ({shift})")
        log(f"等待: {wait_seconds / 3600:.1f} 小时")
        log("=" * 40)

        time.sleep(wait_seconds)
        run_report(shift)
        time.sleep(60)  # 避免同一分钟重复执行


def main():
    log("=" * 50)
    log("EHS 日报后台服务启动")
    log(f"日报脚本: {REPORT_SCRIPT}")
    log(f"Python: {sys.executable}")
    log("=" * 50)

    if not os.path.exists(REPORT_SCRIPT):
        log(f"错误：找不到日报脚本，请确保 ehs_shift_report.py 和本文件在同一目录")
        time.sleep(5)
        return

    # 启动定时器线程
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()

    if HAS_TRAY:
        icon = run_tray()
        if icon:
            icon.run()
    else:
        log("无托盘模式，按 Ctrl+C 停止")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    log("服务已退出")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"服务异常: {e}")
        import traceback
        log(traceback.format_exc())
        time.sleep(5)
