#!/usr/bin/env python3
"""
测试 WeLink Webhook 发送群消息
用法: python3 test_welink.py
"""

import urllib.request
import urllib.error
import json
import uuid
import time

# ⚠️ 把下面的 fc49bc…5f5d 换成你真实的完整 token
WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=fc49bc…5f5d&channel=standard"


def send_text(content: str, is_at: bool = False, is_at_all: bool = False, at_accounts: list = None):
    """
    发送文本消息到 WeLink 群
    
    Args:
        content: 消息内容（1~500字符）
        is_at: 是否@某个人
        is_at_all: 是否@全员
        at_accounts: 被@人员的userid列表，如 ["mettjhfuukaq@562a847505"]
    """
    # WeLink 要求消息长度 1~500
    if len(content) > 500:
        content = content[:497] + "..."
    
    body = {
        "messageType": "text",
        "content": {
            "text": content
        },
        "timeStamp": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()).replace("-", ""),
        "isAt": is_at,
        "isAtAll": is_at_all,
    }
    
    if is_at and at_accounts:
        body["atAccounts"] = at_accounts[:10]  # 最多10个
    
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={
            "Content-Type": "application/json; charset=UTF-8"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            print(f"Status: {resp.status}")
            print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
            return result
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            print(f"Body: {e.read().decode('utf-8')}")
        except:
            pass
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


if __name__ == "__main__":
    # 获取本机公网IP
    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
    except:
        ip = "unknown"
    
    msg = f"【EHS测试】这是一条来自安全联锁系统的测试消息 🧪\n时间：2026-05-28\n发送IP：{ip}"
    
    print(f"发送消息到 WeLink...")
    print(f"本机公网IP: {ip}")
    print(f"消息长度: {len(msg)} 字符\n")
    
    result = send_text(msg)
    
    if result:
        code = result.get("code")
        if code == "0":
            print("\n✅ 发送成功！去群里看看有没有消息。")
        elif code == "58404":
            print("\n❌ 机器人资源不存在，检查 token 是否正确。")
        elif code == "58601":
            print(f"\n❌ 参数错误: {result.get('message')}")
        elif code == "58602":
            print("\n❌ 机器人未启用，检查 WeLink 群机器人状态。")
        else:
            print(f"\n⚠️ 未知错误码 {code}: {result.get('message')}")
    else:
        print("\n❌ 发送失败，检查 IP 白名单和 token 是否正确。")
