import urllib.request
import urllib.error
import json
import uuid
import time
import sys

# ⚠️ 把下面的 fc49bc…5f5d 换成你真实的完整 token（从 WeLink 群机器人设置里复制）
WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=***&channel=standard"


def send_text(content: str):
    if len(content) > 500:
        content = content[:497] + "..."

    body = {
        "messageType": "text",
        "content": {
            "text": content
        },
        "timeStamp": int(time.time() * 1000),
        "uuid": str(uuid.uuid4()).replace("-", ""),
        "isAt": False,
        "isAtAll": False,
    }

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
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            print(f"Body: {e.read().decode('utf-8')}")
        except:
            pass
        return None
    except urllib.error.URLError as e:
        print(f"网络错误: {e.reason}")
        return None
    except Exception as e:
        print(f"其他错误: {e}")
        return None


if __name__ == "__main__":
    print("=" * 50)
    print("WeLink Webhook 推送测试")
    print("=" * 50)

    # 获取本机公网IP
    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode()
    except:
        ip = "unknown"

    msg = f"【EHS测试】来自Windows电脑的测试消息 🧪\n时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n发送IP：{ip}"

    print(f"\n本机公网IP: {ip}")
    print(f"消息长度: {len(msg)} 字符")
    print(f"\n正在发送...\n")

    result = send_text(msg)

    if result:
        code = result.get("code")
        if code == "0":
            print("✅ 发送成功！去 WeLink 群里看看有没有消息。")
        elif code == "58404":
            print("❌ 机器人资源不存在，检查 token 是否正确。")
        elif code == "58601":
            print(f"❌ 参数错误: {result.get('message')}")
        elif code == "58602":
            print("❌ 机器人未启用，检查 WeLink 群机器人状态。")
        else:
            print(f"⚠️ 未知错误码 {code}: {result.get('message')}")
    else:
        print("❌ 发送失败，检查网络连接、IP 白名单和 token 是否正确。")

    print("\n按 Enter 退出...")
    input()
