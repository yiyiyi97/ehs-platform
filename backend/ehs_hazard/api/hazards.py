"""隐患管理 API"""
from fastapi import APIRouter, HTTPException, Query, Depends
from ehs_hazard.models import SessionLocal, HazardRecord
from ehs_hazard.api.auth import get_current_user, require_admin
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import func, case

router = APIRouter()


@router.get("")
def list_hazards(
    page: int = 1, size: int = 50, status: str = "", search: str = "",
    risk_level: str = "", subsystem: str = "", check_type: str = "", floor: str = "",
    lab: str = "",
    version: str = "",
    sort_by: str = "", sort_order: str = "desc",
    user=Depends(get_current_user)
):
    db = SessionLocal()
    try:
        q = db.query(HazardRecord)
        if status: q = q.filter(HazardRecord.status == status)
        if risk_level: q = q.filter(HazardRecord.risk_level == risk_level)
        if subsystem: q = q.filter(HazardRecord.subsystem == subsystem)
        if check_type: q = q.filter(HazardRecord.check_type == check_type)
        if floor: q = q.filter(HazardRecord.floor == floor)
        if lab: q = q.filter(HazardRecord.lab == lab)
        if version: q = q.filter(HazardRecord.version == version)
        if search:
            kw = f"%{search}%"
            q = q.filter(
                (HazardRecord.hazard_no.like(kw)) |
                (HazardRecord.risk_desc.like(kw)) |
                (HazardRecord.reporter.like(kw)) |
                (HazardRecord.responsible_person.like(kw))
            )
        total = q.count()

        # 排序处理
        order_dir = sort_order.lower() if sort_order.lower() in ("asc", "desc") else "desc"
        if sort_by == "report_date":
            col = HazardRecord.report_date
            q = q.order_by(col.asc() if order_dir == "asc" else col.desc())
        elif sort_by == "expected_close_date":
            # 未闭环的按期望闭环日期排序（升序=最紧急在前），已闭环排到最后
            if order_dir == "asc":
                q = q.order_by(
                    case((HazardRecord.status == "closed", 1), else_=0),
                    HazardRecord.expected_close_date.asc()
                )
            else:
                q = q.order_by(
                    case((HazardRecord.status == "closed", 0), else_=1),
                    HazardRecord.expected_close_date.desc()
                )
        else:
            q = q.order_by(HazardRecord.id.desc())

        items = q.offset((page - 1) * size).limit(size).all()
        return {"total": total, "page": page, "size": size, "items": [h.to_dict() for h in items]}
    finally:
        db.close()


@router.get("/{hazard_id}")
def get_hazard(hazard_id: int, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        h = db.query(HazardRecord).get(hazard_id)
        if not h:
            raise HTTPException(404)
        return h.to_dict()
    finally:
        db.close()


@router.post("")
def create_hazard(data: dict, user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        h = HazardRecord(**{k: v for k, v in data.items() if k in HazardRecord.__table__.columns.keys()})
        db.add(h)
        db.commit()
        db.refresh(h)
        return h.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/{hazard_id}")
def update_hazard(hazard_id: int, data: dict, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        h = db.query(HazardRecord).get(hazard_id)
        if not h:
            raise HTTPException(404)
        for k, v in data.items():
            if k in HazardRecord.__table__.columns.keys() and k != "id":
                setattr(h, k, v)
        db.commit()
        return h.to_dict()
    finally:
        db.close()


@router.delete("/{hazard_id}")
def delete_hazard(hazard_id: int, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        h = db.query(HazardRecord).get(hazard_id)
        if not h:
            raise HTTPException(404)
        db.delete(h)
        db.commit()
        return {"ok": True}
    finally:
        db.close()


@router.post("/{hazard_id}/close")
def close_hazard(hazard_id: int, data: dict = {}, user=Depends(require_admin)):
    """闭环"""
    db = SessionLocal()
    try:
        h = db.query(HazardRecord).get(hazard_id)
        if not h:
            raise HTTPException(404)
        h.status = "closed"
        h.close_date = data.get("close_date", "")
        h.verifier = data.get("verifier", h.verifier)
        db.commit()
        return h.to_dict()
    finally:
        db.close()
