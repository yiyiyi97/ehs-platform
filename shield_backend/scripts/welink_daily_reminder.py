#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EHS 安全连锁屏蔽超期提醒 - WeLink 日报推送
用法: python welink_daily_reminder.py

功能:
  1. 从 EHS 服务器获取屏蔽统计数据 (/api/stats)
  2. 获取超期明细 (/api/ledger)
  3. 推送消息到 WeLink 群机器人

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

# @人员配置（可选）
# 格式: ["userid1", "userid2"]
# 注意: userid 需要与 atAccounts 中一致才能实现高亮
AT_ACCOUNTS = json.loads(os.getenv("AT_ACCOUNTS", "[]"))
IS_AT_ALL = os.getenv("IS_AT_ALL", "false").lower() == "true"

# 消息长度限制（WeLink 限制 500 字符）
MAX_MESSAGE_LENGTH = 500

# ═══════════════════════════════════════════════════
# HTTP 请求辅助函数
# ═══════════════════════════════════════════════════

def http_get(url: str, timeout: int = 10) -> dict | None:
    """发送 GET 请求，返回 JSON 数据"""
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except urllib.error.HTTPError as e:
        print(f"[HTTP Error] {e.code}: {e.reason} -> {url}")
        return None
    except Exception as e:
        print(f"[Request Error] {e} -> {url}")
        return None


def send_welink_message(content: str, at_accounts: list = None, is_at_all: bool = False) -> dict | None:
    """发送文本消息到 WeLink"""

    # 截断超长消息
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
        body["atAccounts"] = at_accounts[:10]  # 最多 @10 人

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
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except Exception as e:
        print(f"[WeLink Error] 发送失败: {e}")
        return None


# ═══════════════════════════════════════════════════
# 数据获取
# ═══════════════════════════════════════════════════

def fetch_stats() -> dict | None:
    """获取屏蔽统计数据"""
    url = f"{EHS_BASE_URL}/api/shield/stats"
    data = http_get(url)
    if data and all(k in data for k in ("totalApps", "totalActive", "totalOverdue")):
        return data
    print(f"[Stats] 返回数据格式异常: {data}")
    return None


def fetch_ledger() -> list:
    """获取当前活跃屏蔽清单（用于超期明细）"""
    url = f"{EHS_BASE_URL}/api/shield/ledger"
    data = http_get(url)
    if isinstance(data, list):
        return data
    return []


# ═══════════════════════════════════════════════════
# 消息格式化
# ═══════════════════════════════════════════════════

def format_daily_report(stats: dict, overdue_items: list) -> str:
    """格式化日报消息"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    total_apps = stats.get("totalApps", 0)
    total_active = stats.get("totalActive", 0)
    total_overdue = stats.get("totalOverdue", 0)

    lines = [
        f"【EHS安全联锁日报】{date_str}",
        "━━━━━━━━━━━━━━━━",
        f"当前屏蔽作业：{total_apps} 个",
        f"活跃屏蔽设备：{total_active} 个",
        f"超时未恢复：{total_overdue} 个",
        "",
        f"查看台账：http://10.29.113.101:8000/shield/ledger",
    ]

    # 添加超期明细（最多显示 5 条，避免消息过长）
    if total_overdue > 0 and overdue_items:
        lines.append("")
        lines.append("⚠️ 超期明细：")

        # 只取超期项
        overdue_only = [
            item for item in overdue_items
            if item.get("expected_restore_time") and item.get("expected_restore_time") < datetime.now().isoformat()
        ]

        for i, item in enumerate(overdue_only[:5], 1):
            device = item.get("shield_item_name", "未知设备")
            applicant = item.get("applicant", "未知")
            restore_time = item.get("expected_restore_time", "")
            if restore_time:
                # 简化时间显示
                restore_time = restore_time.replace("T", " ")[:16]
            lines.append(f"{i}. {device} (申请人: {applicant}, 预计恢复: {restore_time})")

        if len(overdue_only) > 5:
            lines.append(f"... 等共 {len(overdue_only)} 条超期记录")

        lines.append("")
        lines.append("请相关人员及时跟进处理！")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════

def main():
    print("=" * 50)
    print("EHS 安全联锁屏蔽超期提醒")
    print("=" * 50)
    print(f"服务器: {EHS_BASE_URL}")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 1. 获取统计数据
    print("[1/3] 获取统计数据...")
    stats = fetch_stats()
    if not stats:
        print("❌ 无法获取统计数据，请检查服务器地址和网络连接")
        return 1
    print(f"   屏蔽作业: {stats['totalApps']}, 活跃设备: {stats['totalActive']}, 超期: {stats['totalOverdue']}")

    # 2. 获取超期明细
    print("[2/3] 获取超期明细...")
    ledger = fetch_ledger()
    print(f"   活跃记录: {len(ledger)} 条")

    # 3. 格式化消息
    print("[3/3] 格式化并推送消息...")
    report = format_daily_report(stats, ledger)
    print(f"\n消息内容 ({len(report)} 字符):\n{'-' * 40}")
    print(report)
    print("-" * 40)

    # 4. 发送到 WeLink
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
        exit_code = 1

    # Windows 环境下暂停（方便查看结果）
    if sys.platform == "win32" and "TASK_SCHEDULER" not in os.environ:
        input("\n按 Enter 退出...")

    sys.exit(exit_code)
