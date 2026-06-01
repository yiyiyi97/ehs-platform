"""EHS Dashboard — Unified FastAPI entry point"""
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Ensure backend dir is on Python path for imports
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from ehs_loto.models import init_db as loto_init_db
    from ehs_hazard.models import init_db as hazard_init_db
    from ehs_incident.models import init_db as incident_init_db
    from ehs_equipment.models import init_db as equipment_init_db
    loto_init_db()
    hazard_init_db()
    incident_init_db()
    equipment_init_db()
    print("EHS Dashboard ready on :8000")
    yield

app = FastAPI(title="EHS Dashboard", version="1.0.0", lifespan=lifespan)

# ── Global exception handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"ERROR: {exc}\n{traceback.format_exc()}")
    return JSONResponse(status_code=500, content={"error": str(exc)})

# ═══════════════════════════════════════════════════════════════
#  LOTO API
# ═══════════════════════════════════════════════════════════════
from ehs_loto.api.devices import router as loto_devices_router
from ehs_loto.api.connections import router as loto_connections_router
from ehs_loto.main import core_router as loto_core_router

app.include_router(loto_devices_router, prefix="/api/loto/devices", tags=["loto-devices"])
app.include_router(loto_connections_router, prefix="/api/loto/connections", tags=["loto-connections"])
app.include_router(loto_core_router, prefix="/api/loto", tags=["loto-core"])

# ═══════════════════════════════════════════════════════════════
#  Hazard API
# ═══════════════════════════════════════════════════════════════
from ehs_hazard.api.auth import router as hazard_auth_router
from ehs_hazard.api.hazards import router as hazard_hazards_router
from ehs_hazard.api.options import router as hazard_options_router
from ehs_hazard.api.excel import router as hazard_excel_router
from ehs_hazard.api.stats import router as hazard_stats_router
from ehs_hazard.main import core_router as hazard_core_router

app.include_router(hazard_auth_router, prefix="/api/hazard/auth", tags=["hazard-auth"])
app.include_router(hazard_hazards_router, prefix="/api/hazard/hazards", tags=["hazard-hazards"])
app.include_router(hazard_options_router, prefix="/api/hazard/options", tags=["hazard-options"])
app.include_router(hazard_excel_router, prefix="/api/hazard/excel", tags=["hazard-excel"])
app.include_router(hazard_stats_router, prefix="/api/hazard/stats", tags=["hazard-stats"])
app.include_router(hazard_core_router, prefix="/api/hazard", tags=["hazard-core"])

# ═══════════════════════════════════════════════════════════════
#  Equipment API
# ═══════════════════════════════════════════════════════════════
from ehs_equipment.api.auth import router as equipment_auth_router
from ehs_equipment.api.equipments import router as equipment_equipments_router
from ehs_equipment.api.options import router as equipment_options_router
from ehs_equipment.api.stats import router as equipment_stats_router
from ehs_equipment.api.excel import router as equipment_excel_router
from ehs_equipment.main import core_router as equipment_core_router

app.include_router(equipment_auth_router, prefix="/api/equipment/auth", tags=["equipment-auth"])
app.include_router(equipment_equipments_router, prefix="/api/equipment/equipments", tags=["equipment-equipments"])
app.include_router(equipment_options_router, prefix="/api/equipment/options", tags=["equipment-options"])
app.include_router(equipment_stats_router, prefix="/api/equipment/stats", tags=["equipment-stats"])
app.include_router(equipment_excel_router, prefix="/api/equipment/excel", tags=["equipment-excel"])
app.include_router(equipment_core_router, prefix="/api/equipment", tags=["equipment-core"])

# ═══════════════════════════════════════════════════════════════
#  Incident API
# ═══════════════════════════════════════════════════════════════
from ehs_incident.api.incidents import router as incident_incidents_router
from ehs_incident.api.stats import router as incident_stats_router
from ehs_incident.api.options import router as incident_options_router
from ehs_incident.api.excel import router as incident_excel_router
from ehs_incident.main import core_router as incident_core_router

app.include_router(incident_incidents_router, prefix="/api/incident/incidents", tags=["incident-incidents"])
app.include_router(incident_stats_router, prefix="/api/incident/stats", tags=["incident-stats"])
app.include_router(incident_options_router, prefix="/api/incident/options", tags=["incident-options"])
app.include_router(incident_excel_router, prefix="/api/incident/excel", tags=["incident-excel"])
app.include_router(incident_core_router, prefix="/api/incident", tags=["incident-core"])

# ═══════════════════════════════════════════════════════════════
#  Shield API
# ═══════════════════════════════════════════════════════════════
from ehs_shield.api.items import router as shield_items_router
from ehs_shield.api.applications import router as shield_applications_router
from ehs_shield.api.stats import router as shield_stats_router
from ehs_shield.api.push import router as shield_push_router
from ehs_shield.main import core_router as shield_core_router

app.include_router(shield_items_router, prefix="/api/shield", tags=["shield-items"])
app.include_router(shield_applications_router, prefix="/api/shield", tags=["shield-applications"])
app.include_router(shield_stats_router, prefix="/api/shield", tags=["shield-stats"])
app.include_router(shield_push_router, prefix="/api/shield", tags=["shield-push"])
app.include_router(shield_core_router, prefix="/api/shield", tags=["shield-core"])

# ═══════════════════════════════════════════════════════════════
#  Safety Officer Schedule API
# ═══════════════════════════════════════════════════════════════
import json
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional

SCHEDULE_FILE = os.path.join(DATA_DIR, "safety_officer.json")

class OfficerSite(BaseModel):
    name: str
    officers: List[str]
    phone: str = ""

class ShiftSchedule(BaseModel):
    sites: List[OfficerSite]

class SchedulePayload(BaseModel):
    date: str
    dayShift: ShiftSchedule
    nightShift: ShiftSchedule

def _load_schedule_all():
    if not os.path.exists(SCHEDULE_FILE):
        return {}
    try:
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def _save_schedule_all(data: dict):
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.get("/api/safety-officer")
def get_schedule(date: str = ""):
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
    all_data = _load_schedule_all()
    return all_data.get(date, {
        "date": date,
        "dayShift": {"sites": []},
        "nightShift": {"sites": []}
    })

@app.post("/api/safety-officer")
def save_schedule(data: SchedulePayload):
    all_data = _load_schedule_all()
    all_data[data.date] = data.model_dump()
    _save_schedule_all(all_data)
    return {"success": True}

SHIELD_UPLOADS_DIR = os.path.join(BASE_DIR, "..", "shield_backend", "uploads")
BACKEND_UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

# Static uploads — 按优先级查找文件
@app.api_route("/uploads/{path:path}", methods=["GET"])
async def serve_uploads(path: str):
    for d in [UPLOADS_DIR, SHIELD_UPLOADS_DIR, BACKEND_UPLOADS_DIR]:
        p = os.path.join(d, path)
        if os.path.isfile(p):
            return FileResponse(p)
    return JSONResponse(status_code=404, content={"error": "文件不存在"})

# ═══════════════════════════════════════════════════════════════
#  Static Files
# ═══════════════════════════════════════════════════════════════
SHIELD_DIR = os.path.join(FRONTEND_DIR, "shield")

@app.get("/shield/{full_path:path}")
def shield_spa(full_path: str):
    fp = os.path.join(SHIELD_DIR, full_path)
    if not os.path.isfile(fp):
        fp = os.path.join(SHIELD_DIR, "index.html")
    r = FileResponse(fp)
    r.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    return r

@app.get("/shield")
@app.get("/shield/")
def shield_index():
    return shield_spa("index.html")

app.mount("/loto", StaticFiles(directory=os.path.join(FRONTEND_DIR, "loto"), html=True), name="loto")
app.mount("/hazard", StaticFiles(directory=os.path.join(FRONTEND_DIR, "hazard"), html=True), name="hazard")
app.mount("/incident", StaticFiles(directory=os.path.join(FRONTEND_DIR, "incident"), html=True), name="incident")
app.mount("/equipment", StaticFiles(directory=os.path.join(FRONTEND_DIR, "equipment"), html=True), name="equipment")

@app.get("/")
def dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
