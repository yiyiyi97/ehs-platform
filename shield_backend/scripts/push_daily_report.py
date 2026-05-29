import urllib.request
import urllib.error
import json
import uuid
import time

# ─── 配置 ─────────────────────────────────────
WELINK_WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=<完整token>&channel=standard"
EHS_API_URL = "http://10.29.113.101:8000/api/stats"  # 先尝试 JSON 接口
# 备用：EHS_PAGE_URL = "http://10.29.113.101:8000/shield/ledge"

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

def get_ehs_stats():
    """从 EHS 服务器获取统计数据"""
    try:
        req = urllib.request.Request(EHS_API_URL, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"[EHS] 获取到数据: {json.dumps(data, ensure_ascii=False)}")
            return data
    except urllib.error.HTTPError as e:
        print(f"[EHS] HTTP {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"[EHS] 请求失败: {e}")
        return None

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
    print("EHS → WeLink 日报推送")
    print("=" * 50)
    
    # 1. 获取 EHS 数据
    print("\n[1/3] 正在获取 EHS 统计数据...")
    stats = get_ehs_stats()
    
    if not stats:
        print("❌ 无法获取 EHS 数据，任务终止")
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
