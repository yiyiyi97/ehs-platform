# WeLink Webhook 推送测试 (PowerShell)
# 用法：右键 → 使用 PowerShell 运行

$WEBHOOK_URL = "https://open.welink.huaweicloud.com/api/werobot/v1/webhook/send?token=***&channel=standard"

# 获取公网IP
try {
    $ip = (Invoke-WebRequest -Uri "https://api.ipify.org" -TimeoutSec 5).Content
} catch {
    $ip = "unknown"
}

# 组装消息
$timestamp = ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds())
$uuid = [guid]::NewGuid().ToString().Replace("-", "")
$msg = "【EHS测试】来自Windows电脑的测试消息 🧪`n时间：$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n发送IP：$ip"

Write-Host "========================================"
Write-Host "WeLink Webhook 推送测试"
Write-Host "========================================"
Write-Host ""
Write-Host "本机公网IP: $ip"
Write-Host "消息长度: $($msg.Length) 字符"
Write-Host ""
Write-Host "正在发送..."
Write-Host ""

$body = @{
    messageType = "text"
    content = @{ text = $msg }
    timeStamp = $timestamp
    uuid = $uuid
    isAt = $false
    isAtAll = $false
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-WebRequest -Uri $WEBHOOK_URL -Method POST `
        -Headers @{ "Content-Type" = "application/json; charset=UTF-8" } `
        -Body $body -TimeoutSec 15
    
    $result = $response.Content | ConvertFrom-Json
    $code = $result.code
    
    if ($code -eq "0") {
        Write-Host "✅ 发送成功！去 WeLink 群里看看有没有消息。" -ForegroundColor Green
    } elseif ($code -eq "58404") {
        Write-Host "❌ 机器人资源不存在，检查 token 是否正确。" -ForegroundColor Red
    } elseif ($code -eq "58601") {
        Write-Host "❌ 参数错误: $($result.message)" -ForegroundColor Red
    } elseif ($code -eq "58602") {
        Write-Host "❌ 机器人未启用，检查 WeLink 群机器人状态。" -ForegroundColor Red
    } else {
        Write-Host "⚠️ 未知错误码 ${code}: $($result.message)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ 发送失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "检查网络连接、IP 白名单和 token 是否正确。" -ForegroundColor Red
}

Write-Host ""
Write-Host "按 Enter 退出..."
Read-Host
