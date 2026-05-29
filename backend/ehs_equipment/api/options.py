"""字段选项管理 API"""
from fastapi import APIRouter, HTTPException, Depends
from ehs_equipment.models import SessionLocal, FieldOption
from ehs_equipment.api.auth import get_current_user, require_admin

router = APIRouter()


@router.get("/fields")
def list_fields(user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(FieldOption).order_by(FieldOption.field_name, FieldOption.sort_order).all()
        result = {}
        for r in rows:
            result.setdefault(r.field_name, []).append(r.to_dict())
        return result
    finally:
        db.close()


@router.get("")
def list_options(field_name: str = "", user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        q = db.query(FieldOption)
        if field_name:
            q = q.filter(FieldOption.field_name == field_name)
        return [r.to_dict() for r in q.order_by(FieldOption.sort_order).all()]
    finally:
        db.close()


@router.post("")
def create_option(data: dict, admin=Depends(require_admin)):
    db = SessionLocal()
    try:
        opt = FieldOption(
            field_name=data.get("field_name", ""),
            value=data.get("value", ""),
            sort_order=data.get("sort_order", 0)
        )
        db.add(opt)
        db.commit()
        return opt.to_dict()
    finally:
        db.close()


@router.put("/{opt_id}")
def update_option(opt_id: int, data: dict, admin=Depends(require_admin)):
    db = SessionLocal()
    try:
        opt = db.query(FieldOption).get(opt_id)
        if not opt:
            raise HTTPException(404)
        opt.value = data.get("value", opt.value)
        opt.sort_order = data.get("sort_order", opt.sort_order)
        db.commit()
        return opt.to_dict()
    finally:
        db.close()


@router.delete("/{opt_id}")
def delete_option(opt_id: int, admin=Depends(require_admin)):
    db = SessionLocal()
    try:
        opt = db.query(FieldOption).get(opt_id)
        if not opt:
            raise HTTPException(404)
        db.delete(opt)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
