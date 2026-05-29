/**
 * 测试 WeLink Webhook 发送消息
 * 用法: npx ts-node scripts/test-welink.ts
 */
const WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=***&channel=standard";

interface WeLinkResponse {
  code: string;
  data: string;
  message: string;
}

async function sendWelinkMessage(
  content: string,
  options?: {
    isAt?: boolean;
    isAtAll?: boolean;
    atAccounts?: string[];
  }
): Promise<WeLinkResponse | null> {
  // WeLink 要求消息长度 1~500
  if (content.length > 500) {
    content = content.slice(0, 497) + "...";
  }

  const body: Record<string, any> = {
    messageType: "text",
    content: {
      text: content,
    },
    timeStamp: Date.now(),
    uuid: crypto.randomUUID().replace(/-/g, ""),
    isAt: options?.isAt ?? false,
    isAtAll: options?.isAtAll ?? false,
  };

  if (options?.isAt && options?.atAccounts && options.atAccounts.length > 0) {
    body.atAccounts = options.atAccounts.slice(0, 10); // 最多10个
  }

  const res = await fetch(WEBHOOK_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json; charset=UTF-8",
    },
    body: JSON.stringify(body),
  });

  const data: WeLinkResponse = await res.json();
  console.log("Status:", res.status);
  console.log("Response:", JSON.stringify(data, null, 2));
  return data;
}

// 测试发送
async function main() {
  const ip = await fetch("https://api.ipify.org", { timeout: 5000 })
    .then((r) => r.text())
    .catch(() => "unknown");

  const msg = `【EHS测试】这是一条来自安全联锁系统的测试消息 🧪\n时间：${new Date().toLocaleString("zh-CN")}\n发送IP：${ip}`;

  console.log("发送消息到 WeLink...");
  console.log("本机公网IP:", ip);
  console.log("消息长度:", msg.length, "字符\n");

  const result = await sendWelinkMessage(msg);

  if (result) {
    switch (result.code) {
      case "0":
        console.log("\n✅ 发送成功！去群里看看有没有消息。");
        break;
      case "58404":
        console.log("\n❌ 机器人资源不存在，检查 token 是否正确。");
        break;
      case "58601":
        console.log(`\n❌ 参数错误: ${result.message}`);
        break;
      case "58602":
        console.log("\n❌ 机器人未启用，检查 WeLink 群机器人状态。");
        break;
      default:
        console.log(`\n⚠️ 未知错误码 ${result.code}: ${result.message}`);
    }
  } else {
    console.log("\n❌ 发送失败，检查 IP 白名单和 token 是否正确。");
  }
}

main().catch(console.error);
