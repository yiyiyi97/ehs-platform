#!/bin/bash
# 单服务器四地域复盘报告路径 patch
# 深圳(8000)、武汉(8001)、北京(8002)、上海(8003)

set -e

BASE_DIR="/root/EHS_docs/documents/异常事件复盘"

echo "=== patch 四个地域的 incidents.py ==="

for cfg in \
    "/root/EHS_Dashboard:深圳:ehs-dashboard" \
    "/root/EHS_Dashboard_wuhan:武汉:ehs-wuhan" \
    "/root/EHS_Dashboard_beijing:北京:ehs-beijing" \
    "/root/EHS_Dashboard_shanghai:上海:ehs-shanghai"
do
    IFS=: read -r dir region svc <<< "$cfg"
    py="$dir/backend/ehs_incident/api/incidents.py"
    
    echo ""
    echo "[$region] $dir"
    
    if [ ! -f "$py" ]; then
        echo "  错误: $py 不存在"
        continue
    fi
    
    # 备份
    cp "$py" "${py}.bak.$(date +%Y%m%d%H%M%S)"
    
    # patch 两行
    sed -i "s|os.getenv(\"EHS_REPORT_BASE\", os.path.join(BASE_DIR, \"uploads\", \"incident\"))|\"$BASE_DIR\"|" "$py"
    sed -i "s|os.getenv(\"EHS_REGION\", \"\")|\"$region\"|" "$py"
    
    # 验证
    grep -n 'REPORT_BASE\|REPORT_DIR' "$py" | head -3 | sed 's/^/  /'
    
    # 重启
    systemctl restart "$svc"
    echo "  ✓ 重启 $svc"
done

echo ""
echo "=== 全部完成 ==="
systemctl status ehs-dashboard ehs-wuhan ehs-beijing ehs-shanghai --no-pager || true
