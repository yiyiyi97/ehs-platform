#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EHS 本地服务 - 供网页按钮调用执行日报推送
监听 localhost:8765，处理跨域请求

用法:
  python ehs_local_service.py          # 前台运行
  python ehs_local_service.py --bg     # 后台运行(Windows下最小化)
"""

import os
import sys
import subprocess
import json
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

# 服务端口
PORT = 8765
# Python 脚本路径（默认同级目录下的 ehs_shift_report.py）
SCRIPT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ehs_shift_report.py")


class CORSRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 简化日志，只打印关键信息
        msg = format % args
        if "GET" in msg or "POST" in msg:
            print(f"[{self.log_date_time_string()}] {msg}")

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_options(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_get(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "script_exists": os.path.exists(SCRIPT_PATH)}).encode())
            return

        if path == "/run-report":
            self._run_report(parsed.query)
            return

        self.send_response(404)
        self.end_headers()

    def do_post(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/run-report":
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8")
            query = ""
            try:
                data = json.loads(body)
                shift = data.get("shift", "")
                query = f"shift={shift}" if shift else ""
            except Exception:
                pass
            self._run_report(query)
            return

        self.send_response(404)
        self.end_headers()

    def _run_report(self, query_str):
        """执行日报脚本并返回结果"""
        cmd = [sys.executable, SCRIPT_PATH]
        if query_str:
            # 解析 query string 添加参数
            if "shift=" in query_str:
                shift = query_str.split("shift=")[1].split("&")[0]
                cmd.extend(["--shift", shift])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                encoding="utf-8",
                errors="replace"
            )
            output = result.stdout
            if result.stderr:
                output += "\n[STDERR]\n" + result.stderr

            success = result.returncode == 0 and "推送成功" in output

            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": success,
                "returncode": result.returncode,
                "output": output
            }, ensure_ascii=False).encode())

        except subprocess.TimeoutExpired:
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": "执行超时(60秒)"
            }).encode())

        except Exception as e:
            self.send_response(200)
            self._set_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "success": False,
                "error": str(e)
            }).encode())


def main():
    parser = argparse.ArgumentParser(description="EHS 本地日报服务")
    parser.add_argument("--port", type=int, default=PORT, help=f"监听端口(默认{PORT})")
    parser.add_argument("--bg", action="store_true", help="后台运行")
    args = parser.parse_args()

    if not os.path.exists(SCRIPT_PATH):
        print(f"[ERR] 找不到日报脚本: {SCRIPT_PATH}")
        print("[INFO] 请确保 ehs_shift_report.py 和本文件在同一目录")
        sys.exit(1)

    server = HTTPServer(("127.0.0.1", args.port), CORSRequestHandler)
    print(f"=" * 50)
    print(f"EHS 本地日报服务已启动")
    print(f"监听地址: http://127.0.0.1:{args.port}")
    print(f"日报脚本: {SCRIPT_PATH}")
    print(f"=" * 50)
    print(f"可用接口:")
    print(f"  GET  http://127.0.0.1:{args.port}/health      - 健康检查")
    print(f"  GET  http://127.0.0.1:{args.port}/run-report  - 执行日报(自动判断班次)")
    print(f"  POST http://127.0.0.1:{args.port}/run-report  - 执行日报(JSON body: {shift: day/night})")
    print(f"=" * 50)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
