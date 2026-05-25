"""LOTO backend — adapted for unified EHS Dashboard"""
from fastapi import APIRouter
from ehs_loto.models import init_db
from ehs_loto.api import devices, connections

# ── 数据版本号（用于前端自动刷新）──
import threading
data_version = threading.Lock()
_current_version = 0

def get_version():
    return _current_version

def bump_version():
    global _current_version
    _current_version += 1
    return _current_version

# ── Core router (mounted at /api/loto in unified app) ──
core_router = APIRouter()

@core_router.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0", "dataVersion": get_version()}

@core_router.get("/sync-info")
def sync_info(site: str = "001"):
    """轻量同步指纹：包含设备数/锁定状态/受影响状态的 hash"""
    from ehs_loto.models import SessionLocal, Device, Connection
    import hashlib
    db = SessionLocal()
    try:
        devices = db.query(Device).filter(Device.site == site).all()
        c_count = db.query(Connection).filter(Connection.site == site).count()
        parts = [f"{d.id}:{1 if d.is_locked else 0}:{1 if d.is_affected else 0}" for d in devices]
        parts.sort()
        parts.append(f"conn:{c_count}")
        fingerprint = hashlib.md5("|".join(parts).encode()).hexdigest()
        return {"fingerprint": fingerprint, "devices": len(devices), "connections": c_count}
    finally:
        db.close()

@core_router.get("/export")
def export_all(site: str = "001"):
    """导出全量数据（兼容原 v3.2 JSON 格式）"""
    from ehs_loto.models import SessionLocal, Device, Connection
    db = SessionLocal()
    try:
        all_devices = db.query(Device).filter(Device.site == site).all()
        all_connections = db.query(Connection).filter(Connection.site == site).all()

        floors = {}
        for d in all_devices:
            floor_key = str(d.floor)
            if floor_key not in floors:
                floors[floor_key] = []
            floors[floor_key].append(d.to_dict())

        return {
            "version": "4.0.0",
            "site": site,
            "exportTime": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "devices": floors,
            "connections": [c.to_dict() for c in all_connections],
            "deviceCounter": len(all_devices) + 1,
            "metadata": {
                "totalDevices": len(all_devices),
                "totalConnections": len(all_connections),
                "floors": sorted(floors.keys()),
            }
        }
    finally:
        db.close()

@core_router.post("/import")
def import_all(data: dict, site: str = "001"):
    """导入全量数据（跨站点自动重新生成 ID 避免主键冲突）"""
    import re, uuid
    from ehs_loto.models import SessionLocal, Device, Connection
    db = SessionLocal()
    try:
        db.query(Connection).filter(Connection.site == site).delete()
        db.query(Device).filter(Device.site == site).delete()

        from ehs_loto.models import Site
        if not db.query(Site).filter(Site.id == site).first():
            db.add(Site(id=site, name=f"场地 {site}"))

        def camel_to_snake(s):
            return re.sub(r'(?<!^)(?=[A-Z])', '_', s).lower()

        from datetime import datetime as dt
        def fix_datetime(v, key):
            if key in ('created_at', 'updated_at') and isinstance(v, str):
                try: return dt.fromisoformat(v.replace('Z', '+00:00'))
                except: return None
            return v

        id_map = {}
        for dev_list in data.get("devices", {}).values():
            for d in dev_list:
                old_id = d.get("id", "")
                if old_id:
                    id_map[old_id] = f"dev_{uuid.uuid4().hex[:16]}"

        for floor, dev_list in data.get("devices", {}).items():
            for d in dev_list:
                mapped = {}
                for k, v in d.items():
                    sk = camel_to_snake(k)
                    if sk in ('from_',): sk = 'from_'
                    if sk not in ('connections', 'label'):
                        mapped[sk] = v
                old_id = mapped.get("id", "")
                if old_id and old_id in id_map:
                    mapped["id"] = id_map[old_id]
                if 'floor' in mapped:
                    try: mapped['floor'] = int(mapped['floor'])
                    except: pass
                mapped['site'] = site
                for k in list(mapped.keys()):
                    mapped[k] = fix_datetime(mapped[k], k)
                db.add(Device(**{k: v for k, v in mapped.items() if k in Device.__table__.columns.keys()}))

        for c in data.get("connections", []):
            mapped = {}
            for k, v in c.items():
                if k == "from": mapped["from_device_id"] = id_map.get(v, v)
                elif k == "to": mapped["to_device_id"] = id_map.get(v, v)
                elif k == "fromFloor": mapped["from_floor"] = int(v)
                elif k == "toFloor": mapped["to_floor"] = int(v)
                elif k == "fromBreakerId": mapped["from_breaker_id"] = v if v else None
                elif k == "label": mapped[k] = v
            old_conn_id = c.get("id", "") if isinstance(c, dict) else ""
            mapped["id"] = f"conn_{uuid.uuid4().hex[:16]}"
            if "from_device_id" in mapped and "to_device_id" in mapped:
                mapped['site'] = site
                db.add(Connection(**{k: v for k, v in mapped.items() if k in Connection.__table__.columns.keys()}))

        db.commit()
        bump_version()
        return {"ok": True, "devices": db.query(Device).filter(Device.site == site).count(), "connections": db.query(Connection).filter(Connection.site == site).count()}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

@core_router.get("/sites")
def list_sites():
    from ehs_loto.models import SessionLocal, Site, Device, Connection
    db = SessionLocal()
    try:
        sites = db.query(Site).all()
        result = []
        for s in sites:
            d_count = db.query(Device).filter(Device.site == s.id).count()
            c_count = db.query(Connection).filter(Connection.site == s.id).count()
            result.append({"id": s.id, "name": s.name, "devices": d_count, "connections": c_count})
        return result
    finally:
        db.close()

@core_router.post("/sites")
def create_site(data: dict):
    from ehs_loto.models import SessionLocal, Site
    db = SessionLocal()
    try:
        sid = data.get("id", "")
        name = data.get("name", sid)
        if not sid: return {"ok": False, "error": "id required"}
        if db.query(Site).filter(Site.id == sid).first():
            return {"ok": False, "error": "site exists"}
        db.add(Site(id=sid, name=name))
        db.commit()
        return {"ok": True}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}
    finally:
        db.close()

@core_router.put("/sites/{site_id}")
def rename_site(site_id: str, data: dict):
    from ehs_loto.models import SessionLocal, Site
    db = SessionLocal()
    try:
        s = db.query(Site).filter(Site.id == site_id).first()
        if not s: return {"ok": False, "error": "not found"}
        s.name = data.get("name", s.name)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@core_router.delete("/sites/{site_id}")
def delete_site(site_id: str):
    from ehs_loto.models import SessionLocal, Site, Device, Connection
    db = SessionLocal()
    try:
        if site_id == "001": return {"ok": False, "error": "默认场地不可删除"}
        db.query(Device).filter(Device.site == site_id).delete()
        db.query(Connection).filter(Connection.site == site_id).delete()
        db.query(Site).filter(Site.id == site_id).delete()
        db.commit()
        return {"ok": True}
    finally:
        db.close()
