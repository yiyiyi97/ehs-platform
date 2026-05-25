"""EHS Dashboard — Unified FastAPI entry point"""
import os
import sys
import subprocess
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, Response
import httpx
import traceback

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "data")
UPLOADS_DIR = os.path.join(BASE_DIR, "..", "uploads")
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")
SHIELD_BACKEND_DIR = os.path.join(BASE_DIR, "..", "shield_backend")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Ensure backend dir is on Python path for imports
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

shield_process = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global shield_process
    # Start Shield Express backend
    shield_env = os.environ.copy()
    shield_env["PORT"] = "3456"
    shield_env["NODE_ENV"] = "production"
    shield_env["UPLOADS_DIR"] = UPLOADS_DIR
    try:
        shield_process = subprocess.Popen(
            ["node", "dist/index.js"],
            cwd=SHIELD_BACKEND_DIR,
            env=shield_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        # Wait for Express to start
        for _ in range(30):
            await asyncio.sleep(0.5)
            try:
                async with httpx.AsyncClient() as client:
                    r = await client.get("http://localhost:3456/api/health", timeout=1.0)
                    if r.status_code == 200:
                        print("Shield backend started on :3456")
                        break
            except Exception:
                pass
        else:
            print("WARNING: Shield backend may not have started properly")
    except Exception as e:
        print(f"Failed to start Shield backend: {e}")
        shield_process = None

    # Init databases
    from ehs_loto.models import init_db as loto_init_db
    from ehs_hazard.models import init_db as hazard_init_db
    from ehs_incident.models import init_db as incident_init_db
    loto_init_db()
    hazard_init_db()
    incident_init_db()
    print("EHS Dashboard ready on :8000")

    yield

    # Shutdown
    if shield_process:
        shield_process.terminate()
        try:
            shield_process.wait(timeout=5)
        except Exception:
            shield_process.kill()

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
#  Shield API Proxy → Express backend (:3456)
# ═══════════════════════════════════════════════════════════════
@app.api_route("/api/shield/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_shield(request: Request, path: str):
    method = request.method
    url = f"http://localhost:3456/api/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    body = await request.body()
    params = str(request.query_params)
    if params:
        url = f"{url}?{params}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
                timeout=60.0,
            )
        except httpx.ConnectError:
            return JSONResponse(status_code=503, content={"error": "Shield backend unavailable"})

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={k: v for k, v in response.headers.items() if k.lower() not in ("transfer-encoding", "content-encoding", "content-length")},
    )

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

# Shield uploads proxy
@app.api_route("/uploads/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_shield_uploads(request: Request, path: str):
    method = request.method
    url = f"http://localhost:3456/uploads/{path}"
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
    body = await request.body()
    params = str(request.query_params)
    if params:
        url = f"{url}?{params}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                content=body,
                timeout=60.0,
            )
        except httpx.ConnectError:
            return JSONResponse(status_code=503, content={"error": "Shield backend unavailable"})

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers={k: v for k, v in response.headers.items() if k.lower() not in ("transfer-encoding", "content-encoding")},
    )

# ═══════════════════════════════════════════════════════════════
#  Static Files
# ═══════════════════════════════════════════════════════════════
# Shield SPA fallback (must be before mount so catch-all works)
@app.get("/shield/{full_path:path}")
def shield_spa(full_path: str):
    file_path = os.path.join(FRONTEND_DIR, "shield", full_path)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(FRONTEND_DIR, "shield", "index.html"))

app.mount("/loto", StaticFiles(directory=os.path.join(FRONTEND_DIR, "loto"), html=True), name="loto")
app.mount("/hazard", StaticFiles(directory=os.path.join(FRONTEND_DIR, "hazard"), html=True), name="hazard")
app.mount("/shield", StaticFiles(directory=os.path.join(FRONTEND_DIR, "shield"), html=True), name="shield")
app.mount("/incident", StaticFiles(directory=os.path.join(FRONTEND_DIR, "incident"), html=True), name="incident")

@app.get("/")
def dashboard():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
