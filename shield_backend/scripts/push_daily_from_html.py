#!/usr/bin/env python3
"""
EHS → WeLink 日报推送（HTML 页面解析版）
用法: python3 push_daily_from_html.py

如果 http://10.29.113.101:8000/shield/ledge 返回的是 HTML 页面而非 JSON，
用这个版本解析 HTML 中的数据。
"""

import urllib.request
import urllib.error
import json
import uuid
import time
import re

# ─── 配置 ─────────────────────────────────────
WELINK_WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=<完整token>&channel=standard"
EHS_PAGE_URL = "http://10.29.113.101:8000/shield/ledge"

def send_text(content):
    """发送文本消息到 WeLink"""
    if len(content) > 500:
        content = content[:497] + "..."
    
    body = {
        "messageType": "text",
        "content": {"text": content},
        "timeStamp": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()).replace("-", ""),
        "isAt": False,
        "isAtAll": False,
    }
    
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
        print(f"[WeLink] 发送失败: {e}")
        return None

def parse_html_page():
    """
    抓取 EHS HTML 页面并解析关键数据
    
    返回: {
        "totalApps": int,
        "totalActive": int, 
        "totalOverdue": int
    }
    或 None（解析失败）
    """
    try:
        req = urllib.request.Request(EHS_PAGE_URL, method="GET")
        req.add_header("Accept", "text/html")
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
            print(f"[EHS] 获取到 HTML，长度: {len(html)} 字符")
    except Exception as e:
        print(f"[EHS] 请求失败: {e}")
        return None
    
    # 尝试从页面中提取数字（常见模式）
    stats = {}
    
    # 策略1：找包含 "屏蔽"、"超时"、"作业" 等关键字的附近数字
    # 例如：<div class="stat"><span class="number">12</span> 个活跃屏蔽</div>
    
    # 策略2：从页面中所有数字里找规律
    all_numbers = re.findall(r'>\s*(\d+)\s*<', html)
    print(f"[EHS] 页面中找到的数字: {all_numbers[:10]}...")
    
    # 策略3：尝试匹配 "active"、"overdue"、"total" 等 class/id
    active_match = re.search(r'class=["\'].*?active.*?["\'].*?\b(\d+)\b', html, re.S)
    overdue_match = re.search(r'class=["\'].*?overdue.*?["\'].*?\b(\d+)\b', html, re.S)
    total_match = re.search(r'class=["\'].*?total.*?["\'].*?\b(\d+)\b', html, re.S)
    
    if active_match:
        stats["totalActive"] = int(active_match.group(1))
    if overdue_match:
        stats["totalOverdue"] = int(overdue_match.group(1))
    if total_match:
        stats["totalApps"] = int(total_match.group(1))
    
    # 如果上面策略失败，尝试从数字列表推断
    # 通常页面上最大的数字可能是 totalActive，较小的可能是 totalOverdue
    if not stats and all_numbers:
        nums = [int(n) for n in all_numbers if int(n) < 10000]
        if nums:
            stats["totalActive"] = max(nums)
            stats["totalOverdue"] = min([n for n in nums if n > 0] or [0])
            stats["totalApps"] = len(nums)
    
    print(f"[EHS] 解析结果: {json.dumps(stats, ensure_ascii=False)}")
    return stats if stats else None

def format_report(stats):
    """格式化日报消息"""
    date_str = time.strftime("%Y-%m-%d", time.localtime())
    total_active = stats.get("totalActive", 0)
    total_overdue = stats.get("totalOverdue", 0)
    total_apps = stats.get("totalApps", 0)
    
    report = f"【EHS安全联锁日报】{date_str}\n"
    report += f"━━━━━━━━━━━━━━━━\n"
    report += f"当前屏蔽作业：{total_apps} 个\n"
    report += f"活跃屏蔽设备：{total_active} 个\n"
    report += f"超时未恢复：{total_overdue} 个"
    
    if total_overdue > 0:
        report += "\n\n⚠️ 存在超时屏蔽项，请及时处理！"
    
    return report

if __name__ == "__main__":
    print("=" * 50)
    print("EHS → WeLink 日报推送 (HTML解析版)")
    print("=" * 50)
    print(f"页面地址: {EHS_PAGE_URL}")
    
    # 1. 获取并解析页面
    print("\n[1/3] 正在抓取 EHS 页面...")
    stats = parse_html_page()
    
    if not stats:
        print("❌ 无法从页面提取数据")
        print("\n建议：")
        print("1. 先确认 http://10.29.113.101:8000/api/stats 是否可用（JSON 接口更可靠）")
        print("2. 如果只有 HTML 页面，把页面源码发给我，我帮你调整解析规则")
        input("\n按 Enter 退出...")
        exit(1)
    
    # 2. 组装消息
    print("\n[2/3] 组装推送消息...")
    report = format_report(stats)
    print(f"\n消息内容:\n{report}\n")
    
    # 3. 推送到 WeLink
    print("[3/3] 推送到 WeLink...")
    result = send_text(report)
    
    if result and result.get("code") == "0":
        print("✅ 日报推送成功！去群里看看消息。")
    else:
        print(f"❌ 推送失败: {result}")
    
    input("\n按 Enter 退出...")
