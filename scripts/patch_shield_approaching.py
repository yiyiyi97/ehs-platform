#!/usr/bin/env python3
"""
Patch shield frontend bundle to add "approaching deadline" (within 24h) yellow warning.

Changes:
  1. Add approaching() helper: diff(expected_restore_time, now) in hours <= 24
  2. Add .approaching-row CSS (yellow background)
  3. Update rowClassName to apply approaching-row
  4. Update expected_restore_time column: type=warning for approaching
  5. Update shield_item_name column: type=warning for approaching
  6. Add approaching count alert banner
"""

import sys

JS_PATH = "/Users/heyi/ehs-platform/frontend/shield/assets/index-Dz_kmWBS.js"


def patch():
    with open(JS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # ── 1. Add approaching() helper right after l=f=>xn(f).isBefore(i) ──
    old1 = "const i=xn(),l=f=>xn(f).isBefore(i),"
    new1 = "const i=xn(),l=f=>xn(f).isBefore(i),appr=f=>{const r=xn(f),n=xn();return r.diff(n,'hours')>0&&r.diff(n,'hours')<=24},"
    if old1 not in content:
        print("[ERR] Cannot find marker 1 (l=function)")
        return False
    content = content.replace(old1, new1, 1)
    print("[OK] 1. Added approaching() helper")

    # ── 2. Append .approaching-row CSS inside the <style> block ──
    old2 = """.overdue-row {
          background-color: #fff2f0 !important;
        }
        .overdue-row:hover > td {
          background-color: #ffccc7 !important;
        }"""
    new2 = """.overdue-row {
          background-color: #fff2f0 !important;
        }
        .overdue-row:hover > td {
          background-color: #ffccc7 !important;
        }
        .approaching-row {
          background-color: #fffbe6 !important;
        }
        .approaching-row:hover > td {
          background-color: #ffe58f !important;
        }"""
    if old2 not in content:
        print("[ERR] Cannot find marker 2 (CSS block)")
        return False
    content = content.replace(old2, new2, 1)
    print("[OK] 2. Added .approaching-row CSS")

    # ── 3. Update rowClassName in ledger table ──
    old3 = 'rowClassName:f=>l(f.expected_restore_time)?"overdue-row":""'
    new3 = 'rowClassName:f=>l(f.expected_restore_time)?"overdue-row":appr(f.expected_restore_time)?"approaching-row":""'
    if old3 not in content:
        print("[ERR] Cannot find marker 3 (rowClassName)")
        return False
    content = content.replace(old3, new3, 1)
    print("[OK] 3. Updated rowClassName")

    # ── 4. Update expected_restore_time column render: add warning type ──
    # Original: render:f=>De.jsx(jT,{type:l(f)?"danger":void 0,children:xn(f).format(...)})
    old4 = 'render:f=>De.jsx(jT,{type:l(f)?"danger":void 0,children:xn(f).format("YYYY-MM-DD HH:mm")})'
    new4 = 'render:f=>De.jsx(jT,{type:l(f)?"danger":appr(f)?"warning":void 0,children:xn(f).format("YYYY-MM-DD HH:mm")})'
    if old4 not in content:
        print("[ERR] Cannot find marker 4 (expected_restore_time column)")
        return False
    content = content.replace(old4, new4, 1)
    print("[OK] 4. Updated expected_restore_time column")

    # ── 5. Update shield_item_name column render: add warning type ──
    # Original: render:(f,d)=>{const m=l(d.expected_restore_time);return De.jsx(jT,{strong:m,type:m?"danger":void 0,children:f})}
    old5 = 'render:(f,d)=>{const m=l(d.expected_restore_time);return De.jsx(jT,{strong:m,type:m?"danger":void 0,children:f})}'
    new5 = 'render:(f,d)=>{const m=l(d.expected_restore_time),n=appr(d.expected_restore_time);return De.jsx(jT,{strong:m||n,type:m?"danger":n?"warning":void 0,children:f})}'
    if old5 not in content:
        print("[ERR] Cannot find marker 5 (shield_item_name column)")
        return False
    content = content.replace(old5, new5, 1)
    print("[OK] 5. Updated shield_item_name column")

    # ── 6. Add approaching count + banner ──
    # Find: c=e.filter(f=>l(f.expected_restore_time)).length
    old6 = "c=e.filter(f=>l(f.expected_restore_time)).length"
    new6 = "c=e.filter(f=>l(f.expected_restore_time)).length,ap=e.filter(f=>appr(f.expected_restore_time)).length"
    if old6 not in content:
        print("[ERR] Cannot find marker 6 (overdue count)")
        return False
    content = content.replace(old6, new6, 1)
    print("[OK] 6. Added approaching count variable")

    # Find the warning banner for overdue and add approaching banner before it
    # Original: c>0&&De.jsx(Av,{message:`注意：当前有 ${c} 条安全联锁已超时未解除，已置顶高亮显示`,type:"warning",showIcon:!0,style:{marginBottom:16}})
    old7 = 'c>0&&De.jsx(Av,{message:`注意：当前有 ${c} 条安全联锁已超时未解除，已置顶高亮显示`,type:"warning",showIcon:!0,style:{marginBottom:16}})'
    new7 = 'ap>0&&De.jsx(Av,{message:`注意：当前有 ${ap} 条安全联锁将在24小时内到期`,type:"warning",showIcon:!0,style:{marginBottom:16}}),c>0&&De.jsx(Av,{message:`注意：当前有 ${c} 条安全联锁已超时未解除，已置顶高亮显示`,type:"error",showIcon:!0,style:{marginBottom:16}})'
    if old7 not in content:
        print("[ERR] Cannot find marker 7 (overdue banner)")
        return False
    content = content.replace(old7, new7, 1)
    print("[OK] 7. Added approaching banner")

    with open(JS_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("\n[Done] Shield bundle patched successfully!")
    return True


if __name__ == "__main__":
    ok = patch()
    sys.exit(0 if ok else 1)
