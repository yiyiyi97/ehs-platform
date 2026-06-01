#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EHS 班次日报 - WeLink 推送
班次：白班 08:30-20:30（20:30 发送日报）、夜班 20:30-08:30（次日 08:30 发送日报）
推送内容：隐患、异常事件、安全联锁屏蔽、设备校验

使用方法：
  python ehs_shift_report.py              # 自动判断班次
  python ehs_shift_report.py --shift day  # 强制发送白班日报
  python ehs_shift_report.py --shift night # 强制发送夜班日报

定时配置（crontab / Windows 任务计划程序）：
  30 08 * * * python3 /path/to/ehs_shift_report.py    # 夜班日报
  30 20 * * * python3 /path/to/ehs_shift_report.py    # 白班日报
"""

import urllib.request
import urllib.error
import json
import uuid
import time
import sys
import os
import argparse
from urllib.parse import quote
from datetime import datetime, timedelta

# ═══════════════════════════════════════════════════════════════
#  配置区域（请根据实际情况修改）
# ═══════════════════════════════════════════════════════════════

# EHS 服务器地址
EHS_BASE_URL = "http://10.29.113.101:8000"

# WeLink Webhook 地址
WELINK_WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=fc49bcb88ee94aaa8f8e77207ccb5f5d&channel=standard"

# EHS 登录账号
EHS_USERNAME = "protector"
EHS_PASSWORD = "protector"

# @人员配置（可选，留空则不@）
AT_ACCOUNTS = []      # 示例: ["zhangsan", "lisi"]
IS_AT_ALL = False

# 描述截断长度
MAX_DESC_LENGTH = 30

# ═══════════════════════════════════════════════════════════════
#  HTTP 请求辅助
# ═══════════════════════════════════════════════════════════════

_auth_token = None


def login() -> str | None:
    """登录获取 token"""
    global _auth_token
    if _auth_token:
        return _auth_token

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
    except Exception as e:
        print(f"[Login Error] {e}")
        return None


def http_get(url: str, timeout: int = 10, need_auth: bool = True) -> dict | None:
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
    except Exception as e:
        print(f"[HTTP Error] {e} -> {url}")
        return None


def send_welink_message(content: str) -> dict | None:
    """发送文本消息到 WeLink"""
    if len(content) > 500:
        content = content[:497] + "..."

    body = {
        "messageType": "text",
        "content": {"text": content},
        "timeStamp": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()).replace("-", ""),
        "isAt": bool(AT_ACCOUNTS) or IS_AT_ALL,
        "isAtAll": IS_AT_ALL,
    }
    if AT_ACCOUNTS and not IS_AT_ALL:
        body["atAccounts"] = AT_ACCOUNTS[:10]

    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        WELINK_WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[WeLink Error] 发送失败: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
#  班次时间计算
# ═══════════════════════════════════════════════════════════════

class ShiftPeriod:
    def __init__(self, shift_type: str, start_dt: datetime, end_dt: datetime):
        self.shift_type = shift_type
        self.start_dt = start_dt
        self.end_dt = end_dt
        self.start_date_str = start_dt.strftime("%Y-%m-%d %H:%M")
        self.end_date_str = end_dt.strftime("%Y-%m-%d %H:%M")
        self.report_date_str = end_dt.strftime("%Y-%m-%d")

    @property
    def name(self) -> str:
        return "白班" if self.shift_type == "day" else "夜班"


def get_shift_period(now: datetime = None, force_shift: str = None) -> ShiftPeriod:
    """根据当前时间判断班次"""
    if now is None:
        now = datetime.now()

    if force_shift:
        shift = force_shift
    else:
        h = now.hour
        shift = "day" if 8 <= h < 20 else "night"

    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start = today.replace(hour=8, minute=30)
    day_end = today.replace(hour=20, minute=30)

    if shift == "day":
        return ShiftPeriod("day", day_start, day_end)
    else:
        if now.hour < 8:
            return ShiftPeriod("night", day_start - timedelta(hours=12), day_start)
        else:
            return ShiftPeriod("night", day_end, day_end + timedelta(hours=12))


# ═══════════════════════════════════════════════════════════════
#  数据获取
# ═══════════════════════════════════════════════════════════════

def fetch_shift_hazards(shift: ShiftPeriod) -> list:
    """获取本班次新增隐患"""
    url = f"{EHS_BASE_URL}/api/hazard/hazards?page=1&size=200&sort_by=report_date&sort_order=desc"
    data = http_get(url)
    if not data or "items" not in data:
        return []

    start_str = shift.start_dt.strftime("%Y-%m-%d")
    end_str = shift.end_dt.strftime("%Y-%m-%d")
    items = data.get("items", [])
    return [item for item in items if start_str <= item.get("report_date", "") <= end_str]


def fetch_hazard_summary() -> dict | None:
    """获取隐患统计"""
    return http_get(f"{EHS_BASE_URL}/api/hazard/stats/summary", need_auth=False)


def fetch_shift_incidents(shift: ShiftPeriod) -> list:
    """获取本班次新增异常事件"""
    url = f"{EHS_BASE_URL}/api/incident/incidents?page=1&size=200&sort_by=report_date&sort_order=desc"
    data = http_get(url)
    if not data or "items" not in data:
        return []

    start_str = shift.start_dt.strftime("%Y-%m-%d")
    end_str = shift.end_dt.strftime("%Y-%m-%d")
    items = data.get("items", [])
    return [item for item in items if start_str <= item.get("report_date", "") <= end_str]


def fetch_incident_unreviewed() -> int:
    """获取未复盘异常事件数量"""
    url = f"{EHS_BASE_URL}/api/incident/incidents?page=1&size=1&status={quote('待复盘')}"
    data = http_get(url)
    if data and "total" in data:
        return data["total"]
    return 0


def fetch_shield_stats() -> dict | None:
    """获取安全联锁屏蔽统计"""
    return http_get(f"{EHS_BASE_URL}/api/shield/stats", need_auth=False)


def fetch_equipment_stats() -> dict | None:
    """获取设备校验统计"""
    return http_get(f"{EHS_BASE_URL}/api/equipment/stats/summary", need_auth=False)


# ═══════════════════════════════════════════════════════════════
#  格式化
# ═══════════════════════════════════════════════════════════════

def truncate(text: str, length: int) -> str:
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", "")
    return text[:length] + "..." if len(text) > length else text


def format_shift_report(shift: ShiftPeriod, hazards: list, hazard_summary: dict | None,
                        incidents: list, unreviewed: int,
                        shield: dict | None, equipment: dict | None) -> str:
    lines = [
        f"【EHS {shift.name}日报】{shift.report_date_str}",
        f"班次时段：{shift.start_date_str} ~ {shift.end_date_str}",
        "━━━━━━━━━━━━━━━━",
    ]

    # ── 隐患 ──
    open_count = hazard_summary.get("by_status", {}).get("open", 0) if hazard_summary else 0
    total_count = hazard_summary.get("total", 0) if hazard_summary else 0
    closed_count = hazard_summary.get("closed", 0) if hazard_summary else 0
    close_rate = hazard_summary.get("closeRate", 0.0) if hazard_summary else 0.0
    overdue_hazards = hazard_summary.get("overdue", 0) if hazard_summary else 0

    lines.append("")
    lines.append(f"【隐患管理】本班次新增 {len(hazards)} 个 | Open {open_count} 个 | 闭环率 {close_rate}%")
    if hazards:
        for i, item in enumerate(hazards[:3], 1):
            risk_type = item.get("risk_type", "其他")
            level = item.get("risk_level", "")
            desc = truncate(item.get("risk_desc", ""), MAX_DESC_LENGTH)
            reporter = item.get("reporter", "")
            level_str = f"-{level}" if level else ""
            lines.append(f"  {i}. {risk_type}{level_str}：{desc}（{reporter}）")
        if len(hazards) > 3:
            lines.append(f"  ... 等共 {len(hazards)} 个")
    if overdue_hazards > 0:
        lines.append(f"  ⚠️ 超期未闭环：{overdue_hazards} 个")

    # ── 异常事件 ──
    lines.append("")
    lines.append(f"【异常事件】本班次新增 {len(incidents)} 个 | 未复盘 {unreviewed} 个")
    if incidents:
        for i, item in enumerate(incidents[:3], 1):
            incident_type = item.get("incident_type", "其他")
            level = item.get("event_level", "")
            desc = truncate(item.get("description", ""), MAX_DESC_LENGTH)
            reporter = item.get("reporter", "")
            level_str = f"-{level}" if level else ""
            lines.append(f"  {i}. {incident_type}{level_str}：{desc}（{reporter}）")
        if len(incidents) > 3:
            lines.append(f"  ... 等共 {len(incidents)} 个")

    # ── 安全联锁 ──
    lines.append("")
    shield_active = shield.get("totalActive", 0) if shield else 0
    shield_overdue = shield.get("totalOverdue", 0) if shield else 0
    lines.append(f"【安全联锁】活跃屏蔽 {shield_active} 个")
    if shield_overdue > 0:
        lines.append(f"  ⚠️ 超时未恢复：{shield_overdue} 个")

    # ── 设备校验 ──
    lines.append("")
    equip_warning = equipment.get("warning", 0) if equipment else 0
    equip_overdue = equipment.get("overdue", 0) if equipment else 0
    lines.append(f"【设备校验】临期 {equip_warning} 台 | 超期 {equip_overdue} 台")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="EHS 班次日报推送")
    parser.add_argument("--shift", choices=["day", "night"], help="强制指定班次（默认按当前时间自动判断）")
    parser.add_argument("--dry-run", action="store_true", help="仅打印报告，不推送")
    args = parser.parse_args()

    print("=" * 50)
    print("EHS 班次日报推送")
    print("=" * 50)
    print(f"服务器: {EHS_BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    shift = get_shift_period(force_shift=args.shift)
    print(f"[班次] {shift.name} ({shift.start_date_str} ~ {shift.end_date_str})")
    print()

    # 1. 隐患
    print("[1/6] 获取本班次隐患...")
    hazards = fetch_shift_hazards(shift)
    print(f"   本班次新增: {len(hazards)} 个")

    # 2. 隐患统计
    print("[2/6] 获取隐患统计...")
    hazard_summary = fetch_hazard_summary()
    if hazard_summary:
        print(f"   总隐患: {hazard_summary.get('total', 0)}, Open: {hazard_summary.get('by_status', {}).get('open', 0)}, 闭环率: {hazard_summary.get('closeRate', 0)}%")
    else:
        print("   ⚠️ 无法获取")

    # 3. 异常事件
    print("[3/6] 获取本班次异常事件...")
    incidents = fetch_shift_incidents(shift)
    print(f"   本班次新增: {len(incidents)} 个")

    # 4. 未复盘异常事件
    print("[4/6] 获取未复盘异常事件...")
    unreviewed = fetch_incident_unreviewed()
    print(f"   未复盘: {unreviewed} 个")

    # 5. 安全联锁
    print("[5/6] 获取安全联锁屏蔽统计...")
    shield_stats = fetch_shield_stats()
    if shield_stats:
        print(f"   活跃: {shield_stats.get('totalActive', 0)}, 超时: {shield_stats.get('totalOverdue', 0)}")
    else:
        print("   ⚠️ 无法获取")

    # 6. 设备校验
    print("[6/6] 获取设备校验统计...")
    equipment_stats = fetch_equipment_stats()
    if equipment_stats:
        print(f"   临期: {equipment_stats.get('warning', 0)}, 超期: {equipment_stats.get('overdue', 0)}")
    else:
        print("   ⚠️ 无法获取")

    # 格式化并推送
    print("\n[推送] 格式化消息...")
    report = format_shift_report(shift, hazards, hazard_summary, incidents, unreviewed, shield_stats, equipment_stats)
    print(f"\n消息内容 ({len(report)} 字符):\n{'-' * 40}")
    print(report)
    print("-" * 40)

    if args.dry_run:
        print("\n[INFO] 干运行模式，不推送")
        return 0

    result = send_welink_message(report)
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

    # Windows 环境下暂停（方便双击查看结果）
    if sys.platform == "win32":
        input("\n按 Enter 退出...")

    sys.exit(exit_code)
