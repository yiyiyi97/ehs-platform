"""统计 API"""
from fastapi import APIRouter, Depends
from ehs_equipment.models import SessionLocal, EquipmentRecord
from ehs_equipment.api.auth import get_current_user_optional
from datetime import datetime, timezone

router = APIRouter()


@router.get("/summary")
def summary(user=Depends(get_current_user_optional)):
    db = SessionLocal()
    try:
        items = db.query(EquipmentRecord).all()
        total = len(items)
        special = sum(1 for i in items if i.equipment_type == "特种设备")
        measure = sum(1 for i in items if i.equipment_type == "计量设备")

        overdue = 0
        warning = 0
        normal = 0
        for item in items:
            cs = item.to_dict().get("check_status", "")
            if cs == "超期":
                overdue += 1
            elif cs == "临期":
                warning += 1
            elif cs == "正常":
                normal += 1

        # 按类别统计
        category_stats = {}
        for item in items:
            cat = item.category or "未分类"
            category_stats[cat] = category_stats.get(cat, 0) + 1

        # 按实验室统计
        lab_stats = {}
        for item in items:
            lab = item.lab or "未分配"
            lab_stats[lab] = lab_stats.get(lab, 0) + 1

        return {
            "total": total,
            "special": special,
            "measure": measure,
            "overdue": overdue,
            "warning": warning,
            "normal": normal,
            "category_stats": category_stats,
            "lab_stats": lab_stats,
        }
    finally:
        db.close()


@router.get("/by-status")
def by_status(user=Depends(get_current_user_optional)):
    db = SessionLocal()
    try:
        items = db.query(EquipmentRecord).all()
        result = {"在用": 0, "停用": 0, "报废": 0}
        for item in items:
            s = item.status or "在用"
            result[s] = result.get(s, 0) + 1
        return result
    finally:
        db.close()
