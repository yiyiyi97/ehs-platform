#!/usr/bin/env python3
"""
EHS → WeLink 日报推送（HTML 解析版）
用法: python3 push_ehs_daily.py

从 http://10.29.113.101:8000/shield/ledge 页面提取数据并推送到 WeLink。
支持多种解析策略，自动匹配页面结构。
"""

import urllib.request
import urllib.error
import json
import uuid
import time
import re

# ─── 配置 ─────────────────────────────────────
WELINK_WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=<完整token>&channel=standard"
EHS_URL = "http://10.29.113.101:8000/shield/ledge"

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

def fetch_html():
    """抓取 EHS 页面 HTML"""
    try:
        req = urllib.request.Request(EHS_URL, method="GET")
        req.add_header("Accept", "text/html")
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            print(f"[EHS] 获取到 HTML，长度: {len(html)} 字符")
            return html
    except Exception as e:
        print(f"[EHS] 请求失败: {e}")
        return None

def try_extract_stats(html):
    """
    尝试从 HTML 中提取屏蔽统计数据。
    使用多种策略，返回 {"totalActive": int, "totalOverdue": int} 或 None。
    """
    
    # ── 策略 1：找 "活跃屏蔽" / "active" 附近数字 ──
    # 例如: <span class="value">12</span> <span class="label">活跃屏蔽</span>
    
    # 策略 1a: 找 "屏蔽" 相关文本附近的数字
    patterns = [
        # 模式: 活跃屏蔽/当前屏蔽 + 数字
        (r'活跃屏蔽.*?\b(\d+)\b', 'totalActive'),
        (r'当前屏蔽.*?\b(\d+)\b', 'totalActive'),
        (r'active.*?(?:count|num|:).*?\b(\d+)\b', 'totalActive'),
        
        # 模式: 超时/超期 + 数字
        (r'超时.*?\b(\d+)\b', 'totalOverdue'),
        (r'超期.*?\b(\d+)\b', 'totalOverdue'),
        (r'overdue.*?(?:count|num|:).*?\b(\d+)\b', 'totalOverdue'),
        
        # 模式: 统计卡片/数据看板上的数字
        (r'屏蔽作业.*?\b(\d+)\b', 'totalApps'),
        (r'屏蔽设备.*?\b(\d+)\b', 'totalActive'),
    ]
    
    stats = {}
    for pattern, key in patterns:
        matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
        if matches:
            # 取第一个匹配
            val = int(matches[0])
            if key not in stats:
                stats[key] = val
                print(f"[解析] 策略1 匹配 '{key}': {val} (pattern: {pattern[:40]}...)")
    
    # ── 策略 2：从所有 <span class="number" 或 data-value 中提取 ──
    number_spans = re.findall(r'<[^\u003e]*?(?:class=["\'].*?\b(?:number|value|count|stat)\b.*?["\']|data-value=["\'](\d+)["\']).*?>\s*(\d+)\s*<', html, re.I)
    if number_spans:
        print(f"[解析] 找到 {len(number_spans)} 个数字标签")
    
    # ── 策略 3：从 Chart.js 或数据脚本中提取 ──
    # SPA 可能把数据放在 <script> 标签里的 JSON
    script_data = re.findall(r'<script[^\u003e]*>(.*?)\u003c/script>', html, re.DOTALL)
    for script in script_data:
        # 找类似 {totalActive: 12, totalOverdue: 3} 的模式
        json_matches = re.findall(r'["\']?totalActive["\']?\s*[:=]\s*(\d+)', script, re.I)
        if json_matches and 'totalActive' not in stats:
            stats['totalActive'] = int(json_matches[0])
            print(f"[解析] 策略3 匹配 totalActive: {json_matches[0]}")
        
        json_matches = re.findall(r'["\']?totalOverdue["\']?\s*[:=]\s*(\d+)', script, re.I)
        if json_matches and 'totalOverdue' not in stats:
            stats['totalOverdue'] = int(json_matches[0])
            print(f"[解析] 策略3 匹配 totalOverdue: {json_matches[0]}")
        
        # 也尝试找中文键名
        json_matches = re.findall(r'["\']?活跃屏蔽["\']?\s*[:=]\s*(\d+)', script, re.I)
        if json_matches and 'totalActive' not in stats:
            stats['totalActive'] = int(json_matches[0])
        
        json_matches = re.findall(r'["\']?超时未恢复["\']?\s*[:=]\s*(\d+)', script, re.I)
        if json_matches and 'totalOverdue' not in stats:
            stats['totalOverdue'] = int(json_matches[0])
    
    # ── 策略 4：从页面中所有较大的数字推断 ──
    # 如果以上都失败，找页面中所有数字，根据大小和位置推断
    if not stats:
        all_numbers = re.findall(r'>\s*(\d+)\s*<', html)
        all_nums = [int(n) for n in all_numbers if int(n) < 10000]
        if all_nums:
            print(f"[解析] 页面中所有数字: {all_nums[:20]}")
            # 通常最大的可能是 totalActive，如果有 0 可能是 totalOverdue
            if len(all_nums) >= 2:
                stats['totalActive'] = max(all_nums)
                stats['totalOverdue'] = min([n for n in all_nums if n >= 0])
                print(f"[解析] 策略4 推断: totalActive={stats['totalActive']}, totalOverdue={stats['totalOverdue']}")
    
    return stats if stats else None

def format_report(stats):
    """格式化日报消息"""
    date_str = time.strftime("%Y-%m-%d", time.localtime())
    total_active = stats.get("totalActive", 0)
    total_overdue = stats.get("totalOverdue", 0)
    total_apps = stats.get("totalApps", total_active)
    
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
    print("EHS → WeLink 日报推送")
    print("=" * 50)
    print(f"页面地址: {EHS_URL}")
    
    # 1. 抓取页面
    print("\n[1/3] 正在抓取 EHS 页面...")
    html = fetch_html()
    if not html:
        print("❌ 无法获取页面")
        input("\n按 Enter 退出...")
        exit(1)
    
    # 2. 提取数据
    print("\n[2/3] 正在解析页面数据...")
    stats = try_extract_stats(html)
    
    if not stats:
        print("❌ 无法从页面提取数据")
        print("\n调试信息：页面关键片段（前 1000 字符）:")
        print(html[:1000])
        print("\n\n建议：")
        print("1. 打开浏览器，按 F12 → Elements，找到显示数字的元素")
        print("2. 告诉我数字附近的 HTML 代码或文字标签")
        print("3. 我会调整解析规则")
        input("\n按 Enter 退出...")
        exit(1)
    
    print(f"\n提取到数据: {json.dumps(stats, ensure_ascii=False)}")
    report = format_report(stats)
    print(f"\n消息内容:\n{report}\n")
    
    # 3. 推送
    print("[3/3] 推送到 WeLink...")
    result = send_text(report)
    
    if result and result.get("code") == "0":
        print("✅ 日报推送成功！去群里看看消息。")
    else:
        print(f"❌ 推送失败: {result}")
    
    input("\n按 Enter 退出...")
