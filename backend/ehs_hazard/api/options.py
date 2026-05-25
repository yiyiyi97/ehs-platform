"""字段选项管理 API"""
from fastapi import APIRouter, HTTPException, Depends
from ehs_hazard.models import SessionLocal, FieldOption
from ehs_hazard.api.auth import get_current_user, require_admin

router = APIRouter()


@router.get("")
def list_options(field: str = ""):
    db = SessionLocal()
    try:
        q = db.query(FieldOption)
        if field:
            q = q.filter(FieldOption.field_name == field)
        return [o.to_dict() for o in q.order_by(FieldOption.field_name, FieldOption.sort_order).all()]
    finally:
        db.close()


@router.get("/fields")
def list_fields():
    """返回所有字段名+其选项"""
    db = SessionLocal()
    try:
        options = db.query(FieldOption).order_by(FieldOption.field_name, FieldOption.sort_order).all()
        fields = {}
        for o in options:
            if o.field_name not in fields:
                fields[o.field_name] = []
            fields[o.field_name].append(o.value)
        return fields
    finally:
        db.close()


@router.post("")
def create_option(data: dict, user=Depends(require_admin)):
    """{field_name, value, sort_order}"""
    db = SessionLocal()
    try:
        o = FieldOption(
            field_name=data["field_name"],
            value=data["value"],
            sort_order=data.get("sort_order", 0)
        )
        db.add(o)
        db.commit()
        return o.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(400, str(e))
    finally:
        db.close()


@router.put("/{option_id}")
def update_option(option_id: int, data: dict, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        o = db.query(FieldOption).get(option_id)
        if not o:
            raise HTTPException(404)
        if "value" in data:
            o.value = data["value"]
        if "sort_order" in data:
            o.sort_order = data["sort_order"]
        db.commit()
        return o.to_dict()
    finally:
        db.close()


@router.delete("/{option_id}")
def delete_option(option_id: int, user=Depends(require_admin)):
    db = SessionLocal()
    try:
        o = db.query(FieldOption).get(option_id)
        if not o:
            raise HTTPException(404)
        db.delete(o)
        db.commit()
        return {"ok": True}
    finally:
        db.close()
