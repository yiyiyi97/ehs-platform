#!/bin/bash
# 直接修改 service 文件加环境变量，一步到位

echo "=== 修改四地域 service 文件 ==="

for cfg in \
    "ehs-dashboard:/root/EHS_Dashboard:深圳:8000" \
    "ehs-wuhan:/root/EHS_Dashboard_wuhan:武汉:8001" \
    "ehs-beijing:/root/EHS_Dashboard_beijing:北京:8002" \
    "ehs-shanghai:/root/EHS_Dashboard_shanghai:上海:8003"
do
    IFS=: read -r svc dir region port <<< "$cfg"
    svc_file="/etc/systemd/system/${svc}.service"
    
    echo ""
    echo "[$svc] $region -> $dir, port $port"
    
    if [ ! -f "$svc_file" ]; then
        echo "  错误: $svc_file 不存在，跳过"
        continue
    fi
    
    # 备份
    cp "$svc_file" "${svc_file}.bak.$(date +%Y%m%d%H%M%S)"
    
    # 删除旧的 EHS_REPORT_BASE/EHS_REGION 行（如果有）
    sed -i '/Environment="EHS_REPORT_BASE/d' "$svc_file"
    sed -i '/Environment="EHS_REGION/d' "$svc_file"
    
    # 在 [Service] 段末尾（ExecStart 之前或之后）插入环境变量
    # 方式：找到 ExecStart= 行，在它前面插入
    sed -i "/^ExecStart=/i Environment=\"EHS_REPORT_BASE=/root/EHS_docs/documents/异常事件复盘\"\nEnvironment=\"EHS_REGION=$region\"" "$svc_file"
    
    echo "  ✓ 已注入环境变量"
done

echo ""
echo "=== 重载 & 重启 ==="
systemctl daemon-reload

for svc in ehs-dashboard ehs-wuhan ehs-beijing ehs-shanghai; do
    systemctl restart "$svc" 2>&1 && echo "[$svc] 重启成功" || echo "[$svc] 重启失败"
done

echo ""
echo "=== 验证环境变量 ==="
sleep 1
for svc in ehs-dashboard ehs-wuhan ehs-beijing ehs-shanghai; do
    pid=$(systemctl show "$svc" --property=MainPID --value 2>/dev/null)
    if [ "$pid" != "0" ] && [ -n "$pid" ]; then
        echo "[$svc] PID=$pid:"
        grep -z "EHS_REPORT_BASE\|EHS_REGION" /proc/$pid/environ 2>/dev/null | tr '\0' '\n' | sed 's/^/  /'
    else
        echo "[$svc] 未运行"
    fi
done

echo ""
echo "=== 验证目录可写 ==="
for region in 深圳 武汉 北京 上海; do
    target="/root/EHS_docs/documents/异常事件复盘/$region"
    if touch "$target/.write-test" 2>/dev/null; then
        rm -f "$target/.write-test"
        echo "[$region] $target 可写入 ✓"
    else
        echo "[$region] $target 不可写入 ✗ (检查权限)"
    fi
done
