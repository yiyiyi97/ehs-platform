#!/usr/bin/env python3
"""
EHS 服务器接口探测工具
用法: python3 probe_ehs.py

探测 http://10.29.113.101:8000 上有哪些可用接口和数据格式。
"""

import urllib.request
import urllib.error
import json

BASE_URL = "http://10.29.113.101:8000"

ENDPOINTS = [
    "/api/stats",
    "/api/ledger",
    "/api/history",
    "/api/applications",
    "/api/shield-items",
    "/shield/ledge",
    "/shield",
    "/",
]

def probe(url):
    print(f"\n{'='*60}")
    print(f"探测: {url}")
    print(f"{'='*60}")
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "*/*")
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "unknown")
            body = resp.read()
            print(f"Status: {resp.status}")
            print(f"Content-Type: {content_type}")
            
            # 判断是 JSON 还是 HTML
            if "json" in content_type.lower():
                data = json.loads(body.decode("utf-8"))
                print(f"JSON 数据:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
                return {"type": "json", "data": data}
            else:
                text = body.decode("utf-8", errors="ignore")
                print(f"文本/HTML 前 500 字符:\n{text[:500]}...")
                return {"type": "html", "preview": text[:500]}
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    print("EHS 服务器接口探测")
    print(f"目标: {BASE_URL}")
    
    results = {}
    for endpoint in ENDPOINTS:
        results[endpoint] = probe(BASE_URL + endpoint)
    
    print(f"\n{'='*60}")
    print("探测完成，可用接口汇总:")
    print(f"{'='*60}")
    for endpoint, result in results.items():
        if result:
            print(f"  ✅ {endpoint} -> {result['type'].upper()}")
        else:
            print(f"  ❌ {endpoint} -> 不可用")
    
    input("\n按 Enter 退出...")
