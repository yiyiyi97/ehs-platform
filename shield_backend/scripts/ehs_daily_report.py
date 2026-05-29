#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EHS 综合日报 - WeLink 推送
用法: python ehs_daily_report.py

功能:
  1. 今日新增异常事件（含描述）
  2. 今日新增隐患（含描述）
  3. 超期未闭环隐患数量
  4. 安全连锁屏蔽项数
  5. 超期未恢复项数

运行环境: Windows / Python 3.8+
定时配置: Windows 任务计划程序，每天早上 8:30 运行
"""

import urllib.request
import urllib.error
import json
import uuid
import time
import sys
import os
from datetime import datetime

# ═══════════════════════════════════════════════════
# 配置区域（请根据实际情况修改）
# ═══════════════════════════════════════════════════

# EHS 服务器地址（内网）
EHS_BASE_URL = os.getenv("EHS_BASE_URL", "http://10.29.113.101:8000")

# WeLink Webhook 地址
WELINK_WEBHOOK_URL = os.getenv(
    "WELINK_WEBHOOK_URL",
    "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=fc49bcb88ee94aaa8f8e77207ccb5f5d&channel=standard"
)

# EHS 登录账号（用于访问需要认证的接口）
# 默认用户名 protector / 密码 protector（系统内置管理员）
EHS_USERNAME = os.getenv("EHS_USERNAME", "protector")
EHS_PASSWORD = os.getenv("EHS_PASSWORD", "protector")

# @人员配置（可选）
AT_ACCOUNTS = json.loads(os.getenv("AT_ACCOUNTS", "[]"))
IS_AT_ALL = os.getenv("IS_AT_ALL", "false").lower() == "true"

# 消息长度限制（WeLink 限制 500 字符）
MAX_MESSAGE_LENGTH = 500

# 描述截断长度（避免单条描述过长）
MAX_DESC_LENGTH = 30

# ═══════════════════════════════════════════════════
# HTTP 请求辅助函数
# ═══════════════════════════════════════════════════

_auth_token = None


def login() -> str | None:
    """登录获取 token"""
    global _auth_token
    if _auth_token:
        return _auth_token

    if not EHS_USERNAME or not EHS_PASSWORD:
        return None

    url = f"{EHS_BASE_URL}/api/hazard/auth/login"
    body = json.dumps({"username": EHS_USERNAME, "password": EHS_PASSWORD}, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _auth_token = data.get("token")
            if _auth_token:
                print(f"   登录成功: {EHS_USERNAME}")
            return _auth_token
    except urllib.error.HTTPError as e:
        print(f"[Login Error] {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[Login Error] {e}")
        return None


def http_get(url: str, timeout: int = 10, need_auth: bool = False) -> dict | None:
    """发送 GET 请求，返回 JSON 数据"""
    headers = {"Accept": "application/json"}

    if need_auth:
        token = login()
        if token:
            headers["Authorization"] = f"Bearer {token}"

    try:
        req = urllib.request.Request(url, method="GET", headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[HTTP Error] {e.code}: {e.reason} -> {url}")
        return None
    except Exception as e:
        print(f"[Request Error] {e} -> {url}")
        return None


def send_welink_message(content: str, at_accounts: list = None, is_at_all: bool = False) -> dict | None:
    """发送文本消息到 WeLink"""

    if len(content) > MAX_MESSAGE_LENGTH:
        content = content[:MAX_MESSAGE_LENGTH - 3] + "..."

    body = {
        "messageType": "text",
        "content": {"text": content},
        "timeStamp": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()).replace("-", ""),
        "isAt": bool(at_accounts) or is_at_all,
        "isAtAll": is_at_all,
    }

    if at_accounts and not is_at_all:
        body["atAccounts"] = at_accounts[:10]

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")

    req = urllib.request.Request(
        WELINK_WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json; charset=UTF-8",
            "Accept-Charset": "UTF-8",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WeLink Error] 发送失败: {e}")
        return None


# ═══════════════════════════════════════════════════
# 数据获取
# ═══════════════════════════════════════════════════

def fetch_today_incidents() -> list:
    """获取今日新增异常事件"""
    url = f"{EHS_BASE_URL}/api/incident/incidents?page=1&size=50&sort_by=report_date&sort_order=desc"
    data = http_get(url, need_auth=True)
    if not data or "items" not in data:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    items = data.get("items", [])
    today_items = [item for item in items if item.get("report_date", "").startswith(today)]
    return today_items


def fetch_today_hazards() -> list:
    """获取今日新增隐患"""
    url = f"{EHS_BASE_URL}/api/hazard/hazards?page=1&size=50&sort_by=report_date&sort_order=desc"
    data = http_get(url, need_auth=True)
    if not data or "items" not in data:
        return []

    today = datetime.now().strftime("%Y-%m-%d")
    items = data.get("items", [])
    today_items = [item for item in items if item.get("report_date", "").startswith(today)]
    return today_items


def fetch_hazard_summary() -> dict | None:
    """获取隐患统计摘要（含超期数量）"""
    url = f"{EHS_BASE_URL}/api/hazard/stats/summary"
    return http_get(url, need_auth=False)


def fetch_shield_stats() -> dict | None:
    """获取安全连锁屏蔽统计"""
    url = f"{EHS_BASE_URL}/api/shield/stats"
    return http_get(url, need_auth=False)


# ═══════════════════════════════════════════════════
# 消息格式化
# ═══════════════════════════════════════════════════

def truncate(text: str, length: int) -> str:
    """截断文本"""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", "")
    return text[:length] + "..." if len(text) > length else text


def format_daily_report(incidents: list, hazards: list, hazard_summary: dict | None, shield_stats: dict | None) -> str:
    """格式化综合日报消息"""
    date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [f"【EHS综合日报】{date_str}", "━━━━━━━━━━━━━━━━"]

    # ── 异常事件 ──
    lines.append("")
    lines.append(f"【异常事件】今日新增 {len(incidents)} 个")
    if incidents:
        for i, item in enumerate(incidents[:3], 1):
            incident_type = item.get("incident_type", "其他")
            level = item.get("event_level", "")
            desc = truncate(item.get("description", ""), MAX_DESC_LENGTH)
            reporter = item.get("reporter", "")
            level_str = f"-{level}" if level else ""
            lines.append(f"{i}. {incident_type}{level_str}：{desc}（{reporter}）")
        if len(incidents) > 3:
            lines.append(f"... 等共 {len(incidents)} 个")

    # ── 隐患管理 ──
    lines.append("")
    lines.append(f"【隐患管理】今日新增 {len(hazards)} 个")
    if hazards:
        for i, item in enumerate(hazards[:3], 1):
            risk_type = item.get("risk_type", "其他")
            level = item.get("risk_level", "")
            desc = truncate(item.get("risk_desc", ""), MAX_DESC_LENGTH)
            reporter = item.get("reporter", "")
            level_str = f"-{level}" if level else ""
            lines.append(f"{i}. {risk_type}{level_str}：{desc}（{reporter}）")
        if len(hazards) > 3:
            lines.append(f"... 等共 {len(hazards)} 个")

    overdue_hazards = hazard_summary.get("overdue", 0) if hazard_summary else 0
    if overdue_hazards > 0:
        lines.append(f"⚠️ 超期未闭环隐患：{overdue_hazards} 个")

    # ── 安全联锁 ──
    lines.append("")
    shield_active = shield_stats.get("totalActive", 0) if shield_stats else 0
    shield_overdue = shield_stats.get("totalOverdue", 0) if shield_stats else 0
    lines.append(f"【安全联锁】活跃屏蔽 {shield_active} 个")
    if shield_overdue > 0:
        lines.append(f"⚠️ 超期未恢复：{shield_overdue} 个")
    lines.append(f"查看台账：http://10.29.113.101:8000/shield/ledger")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════

def main():
    print("=" * 50)
    print("EHS 综合日报推送")
    print("=" * 50)
    print(f"服务器: {EHS_BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 今日异常事件
    print("[1/4] 获取今日异常事件...")
    incidents = fetch_today_incidents()
    print(f"   今日新增: {len(incidents)} 个")

    # 2. 今日隐患
    print("[2/4] 获取今日隐患...")
    hazards = fetch_today_hazards()
    print(f"   今日新增: {len(hazards)} 个")

    # 3. 隐患统计
    print("[3/4] 获取隐患统计...")
    hazard_summary = fetch_hazard_summary()
    if hazard_summary:
        print(f"   总隐患: {hazard_summary.get('total', 0)}, 超期未闭环: {hazard_summary.get('overdue', 0)}")
    else:
        print("   ⚠️ 无法获取隐患统计")

    # 4. 安全连锁屏蔽
    print("[4/4] 获取安全连锁屏蔽统计...")
    shield_stats = fetch_shield_stats()
    if shield_stats:
        print(f"   活跃屏蔽: {shield_stats.get('totalActive', 0)}, 超期: {shield_stats.get('totalOverdue', 0)}")
    else:
        print("   ⚠️ 无法获取屏蔽统计")

    # 5. 格式化并推送
    print("\n[5/5] 格式化并推送消息...")
    report = format_daily_report(incidents, hazards, hazard_summary, shield_stats)
    print(f"\n消息内容 ({len(report)} 字符):\n{'-' * 40}")
    print(report)
    print("-" * 40)

    result = send_welink_message(report, AT_ACCOUNTS, IS_AT_ALL)

    if result is None:
        print("❌ 网络错误，消息发送失败")
        return 1

    if result.get("code") == "0":
        print("✅ 消息推送成功！")
        return 0
    else:
        print(f"❌ 推送失败: code={result.get('code')}, message={result.get('message')}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
    except KeyboardInterrupt:
        print("\n已取消")
        exit_code = 130
    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        exit_code = 1

    # Windows 环境下暂停（方便查看结果）
    if sys.platform == "win32" and "TASK_SCHEDULER" not in os.environ:
        input("\n按 Enter 退出...")

    sys.exit(exit_code)
