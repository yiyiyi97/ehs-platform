"""设备台账 API"""
from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File
from ehs_equipment.models import SessionLocal, EquipmentRecord
from ehs_equipment.api.auth import get_current_user, require_admin
from ehs_equipment.models import log_audit
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import os

router = APIRouter()

UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "uploads", "equipment")
os.makedirs(UPLOADS_DIR, exist_ok=True)


def _calc_next_check_date(last_check_date: str, cycle_months: int) -> str:
    """根据上次校验日期和周期计算下次校验日期"""
    last = datetime.strptime(last_check_date, "%Y-%m-%d")
    total_months = last.month + cycle_months - 1  # 0-based
    new_year = last.year + total_months // 12
    new_month = total_months % 12 + 1
    next_date = last.replace(year=new_year, month=new_month)
    return next_date.strftime("%Y-%m-%d")


@router.get("")
def list_equipments(
    page: int = 1, size: int = 50, search: str = "",
    equipment_type: str = "", category: str = "", lab: str = "",
    floor: str = "", status: str = "", check_status: str = "",
    sort_by: str = "", sort_order: str = "desc",
    user=Depends(get_current_user)
):
    db = SessionLocal()
    try:
        q = db.query(EquipmentRecord)
        if equipment_type: q = q.filter(EquipmentRecord.equipment_type == equipment_type)
        if category: q = q.filter(EquipmentRecord.category == category)
        if lab: q = q.filter(EquipmentRecord.lab == lab)
        if floor: q = q.filter(EquipmentRecord.floor == floor)
        if status: q = q.filter(EquipmentRecord.status == status)
        if search:
            kw = f"%{search}%"
            q = q.filter(
                (EquipmentRecord.equipment_no.like(kw)) |
                (EquipmentRecord.equipment_name.like(kw)) |
                (EquipmentRecord.responsible_person.like(kw)) |
                (EquipmentRecord.location.like(kw))
            )

        items_all = q.all()
        total = len(items_all)

        # 计算校验状态并过滤
        enriched = []
        for item in items_all:
            d = item.to_dict()
            if check_status and d.get("check_status") != check_status:
                continue
            enriched.append(d)

        total_filtered = len(enriched)

        # 排序：超期置顶 > 临期其次 > 其他按指定字段排序
        def sort_key(x):
            cs = x.get("check_status", "")
            priority = 0 if cs == "超期" else (1 if cs == "临期" else 2)
            if sort_by == "next_check_date":
                try:
                    ts = datetime.strptime(x.get("next_check_date", ""), "%Y-%m-%d").timestamp()
                except Exception:
                    ts = 0
                # 升序=日期近的在前（超期日期最小排最前），降序=日期远的在前
                return (priority, ts if sort_order == "asc" else -ts)
            elif sort_by == "equipment_no":
                return (priority, x.get("equipment_no", ""))
            elif sort_by == "created_at":
                return (priority, x.get("created_at", ""))
            else:
                # 默认按ID降序（新创建在前），但超期临期置顶
                return (priority, -x.get("id", 0))

        enriched.sort(key=sort_key)

        start = (page - 1) * size
        paged = enriched[start:start + size]

        return {"total": total_filtered, "page": page, "size": size, "items": paged}
    finally:
        db.close()


@router.get("/{equipment_id}")
def get_equipment(equipment_id: int, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        item = db.query(EquipmentRecord).get(equipment_id)
        if not item:
            raise HTTPException(404)
        return item.to_dict()
    finally:
        db.close()


@router.post("")
def create_equipment(data: dict, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        # 自动计算下次校验日期
        if data.get("last_check_date") and data.get("check_cycle"):
            try:
                data["next_check_date"] = _calc_next_check_date(data["last_check_date"], int(data["check_cycle"]))
            except Exception:
                pass

        item = EquipmentRecord(**{k: v for k, v in data.items() if k in EquipmentRecord.__table__.columns.keys()})
        db.add(item)
        db.commit()
        db.refresh(item)
        result = item.to_dict()
        log_audit(user, "create", "equipment", target_id=result.get("id"), target_name=result.get("equipment_no"), after=result)
        return result
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/{equipment_id}")
def update_equipment(equipment_id: int, data: dict, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        item = db.query(EquipmentRecord).get(equipment_id)
        if not item:
            raise HTTPException(404)

        before = item.to_dict()

        for k, v in data.items():
            if k in EquipmentRecord.__table__.columns.keys() and k != "id":
                setattr(item, k, v)

        # 如果更新了上次校验日期或校验周期，重新计算下次校验日期
        if ("last_check_date" in data or "check_cycle" in data) and item.last_check_date and item.check_cycle:
            try:
                item.next_check_date = _calc_next_check_date(item.last_check_date, int(item.check_cycle))
            except Exception:
                pass

        db.commit()
        result = item.to_dict()
        log_audit(user, "update", "equipment", target_id=equipment_id, target_name=result.get("equipment_no"), before=before, after=result)
        return result
    finally:
        db.close()


@router.delete("/{equipment_id}")
def delete_equipment(equipment_id: int, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        item = db.query(EquipmentRecord).get(equipment_id)
        if not item:
            raise HTTPException(404)
        before = item.to_dict()
        # 删除关联图片
        if item.cert_photo:
            try:
                photo_path = os.path.join(UPLOADS_DIR, os.path.basename(item.cert_photo))
                if os.path.exists(photo_path):
                    os.remove(photo_path)
            except Exception:
                pass
        db.delete(item)
        db.commit()
        log_audit(user, "delete", "equipment", target_id=equipment_id, target_name=before.get("equipment_no"), before=before)
        return {"ok": True}
    finally:
        db.close()


@router.post("/upload")
def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    """上传设备证照图片"""
    import uuid as uuid_mod
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid_mod.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOADS_DIR, filename)
    try:
        with open(filepath, "wb") as f:
            f.write(file.file.read())
        url = f"/uploads/equipment/{filename}"
        log_audit(user, "upload", "equipment", target_name=filename, detail=f"上传证照: {file.filename}")
        return {"url": url, "filename": filename}
    except Exception as e:
        raise HTTPException(400, f"上传失败: {str(e)}")
