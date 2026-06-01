"""安全联锁屏蔽 — 联锁项管理"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from ehs_shield.models import ShieldItem, ApplicationItem, get_db

router = APIRouter()


@router.get("/items")
def list_items(version: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(ShieldItem)
    if version:
        q = q.filter(ShieldItem.version == version)
    return q.order_by(ShieldItem.id).all()


@router.get("/items/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ShieldItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="联锁项不存在")
    return item.to_dict()


@router.post("/items")
def create_item(data: dict, db: Session = Depends(get_db)):
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    item = ShieldItem(
        name=name,
        category=data.get("category", ""),
        subsystem=data.get("subsystem", ""),
        version=data.get("version", ""),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item.to_dict()


@router.put("/items/{item_id}")
def update_item(item_id: int, data: dict, db: Session = Depends(get_db)):
    item = db.query(ShieldItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="联锁项不存在")
    if "name" in data and not data["name"].strip():
        raise HTTPException(status_code=400, detail="名称不能为空")
    for field in ["name", "category", "subsystem", "version"]:
        if field in data:
            setattr(item, field, data[field])
    db.commit()
    return item.to_dict()


@router.delete("/items/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(ShieldItem).get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="联锁项不存在")
    ref_count = db.query(ApplicationItem).filter(ApplicationItem.shield_item_id == item_id).count()
    if ref_count > 0:
        raise HTTPException(status_code=400, detail="该联锁项已被引用，无法删除")
    db.delete(item)
    db.commit()
    return {"ok": True}


@router.post("/items/import")
def import_items(data: dict, db: Session = Depends(get_db)):
    items = data.get("items", [])
    import_version = data.get("version", "")
    if not isinstance(items, list) or len(items) == 0:
        raise HTTPException(status_code=400, detail="请提供有效的项目数组")
    count = 0
    for item in items:
        if not item.get("name", "").strip():
            continue
        db.add(ShieldItem(
            name=item["name"].strip(),
            category=item.get("category", ""),
            subsystem=item.get("subsystem", ""),
            version=import_version,
        ))
        count += 1
    db.commit()
    return {"imported": count}
