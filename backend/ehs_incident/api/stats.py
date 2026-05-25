"""异常事件 BI 数据分析 API"""
from fastapi import APIRouter, Depends
from ehs_incident.models import SessionLocal, IncidentRecord
from ehs_incident.api.auth import get_current_user, get_current_user_optional
from sqlalchemy import func
from datetime import datetime, timedelta
import calendar
import json

router = APIRouter()

TREND_DENSITY_MAP = {
    "day":   ("%Y-%m-%d", lambda d: d, 1),
    "week":  ("%Y-%W",    lambda d: d - timedelta(days=d.weekday()), 7),
    "month": ("%Y-%m",    lambda d: d.replace(day=1), 0),
}


def get_density_sql(col, density):
    fmt, offset_fn, _ = TREND_DENSITY_MAP[density]
    return func.strftime(fmt, col), offset_fn


def fill_date_range(start, end, density):
    fmt, offset_fn, step_days = TREND_DENSITY_MAP[density]
    labels = []
    cur = offset_fn(start)
    if density == "month":
        while cur <= end:
            labels.append(cur.strftime(fmt))
            _, last_day = calendar.monthrange(cur.year, cur.month)
            cur += timedelta(days=last_day)
    else:
        while cur <= end:
            labels.append(cur.strftime(fmt))
            cur += timedelta(days=step_days)
    return labels


def clean_date_str(val):
    if val is None:
        return ""
    s = str(val)[:10]
    return s


@router.get("/aggregate")
def aggregate(group_by: str = "incident_type", metric: str = "count", filters: str = "", user=Depends(get_current_user_optional)):
    db = SessionLocal()
    try:
        valid_fields = {
            "incident_type", "event_level", "lab", "version",
            "subsystem", "device_name", "status", "reporter"
        }
        if group_by not in valid_fields:
            return {"labels": [], "values": []}

        q = db.query(
            getattr(IncidentRecord, group_by),
            func.count(IncidentRecord.id)
        )
        if filters:
            try:
                flt = json.loads(filters)
                for k, v in flt.items():
                    if v and k in valid_fields:
                        col = getattr(IncidentRecord, k, None)
                        if col is not None:
                            q = q.filter(col == v)
            except:
                pass

        rows = q.group_by(getattr(IncidentRecord, group_by)).order_by(func.count(IncidentRecord.id).desc()).all()
        labels = [r[0] or "未填写" for r in rows]
        values = [r[1] for r in rows]
        return {"labels": labels, "values": values}
    finally:
        db.close()


@router.get("/summary")
def summary(user=Depends(get_current_user_optional)):
    db = SessionLocal()
    try:
        total = db.query(IncidentRecord).count()
        by_status = dict(db.query(IncidentRecord.status, func.count(IncidentRecord.id)).group_by(IncidentRecord.status).all())
        by_level = dict(db.query(IncidentRecord.event_level, func.count(IncidentRecord.id)).group_by(IncidentRecord.event_level).all())
        by_type = dict(db.query(IncidentRecord.incident_type, func.count(IncidentRecord.id)).group_by(IncidentRecord.incident_type).all())
        with_report = db.query(IncidentRecord).filter(IncidentRecord.review_report_path != "").count()
        return {
            "total": total,
            "by_status": by_status,
            "by_level": by_level,
            "by_type": by_type,
            "with_report": with_report
        }
    finally:
        db.close()


@router.get("/trend")
def trend(days: int = 30, density: str = "day", user=Depends(get_current_user_optional)):
    db = SessionLocal()
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        fmt, offset_fn = get_density_sql(IncidentRecord.report_date, density)
        expr = func.strftime(fmt, IncidentRecord.report_date)

        rows = db.query(expr, func.count(IncidentRecord.id)).filter(
            IncidentRecord.report_date >= start_date,
            IncidentRecord.report_date != ""
        ).group_by(expr).order_by(expr).all()

        now = datetime.now()
        start_dt = offset_fn(datetime.strptime(start_date, "%Y-%m-%d"))
        date_range = fill_date_range(start_dt, now, density)

        data_map = {clean_date_str(r[0]): r[1] for r in rows}
        labels = []
        values = []
        for d in date_range:
            labels.append(d)
            values.append(data_map.get(d, 0))

        return {"labels": labels, "values": values}
    finally:
        db.close()


@router.get("/cross")
def cross_analysis(x_field: str = "event_level", y_field: str = "incident_type", user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        valid = {"incident_type", "event_level", "lab", "version", "subsystem", "device_name", "status"}
        if x_field not in valid or y_field not in valid:
            return {"labels": [], "series": []}

        rows = db.query(
            getattr(IncidentRecord, x_field),
            getattr(IncidentRecord, y_field),
            func.count(IncidentRecord.id)
        ).group_by(
            getattr(IncidentRecord, x_field),
            getattr(IncidentRecord, y_field)
        ).all()

        x_values = sorted(set(r[0] or "未填写" for r in rows))
        y_values = sorted(set(r[1] or "未填写" for r in rows))

        data_map = {}
        for x, y, cnt in rows:
            data_map[(x or "未填写", y or "未填写")] = cnt

        series = []
        for yv in y_values:
            series.append({
                "name": yv,
                "data": [data_map.get((xv, yv), 0) for xv in x_values]
            })

        return {"labels": x_values, "series": series}
    finally:
        db.close()


@router.get("/trend-lab")
def trend_lab(days: int = 30, density: str = "day", user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        fmt, offset_fn = get_density_sql(IncidentRecord.report_date, density)
        expr = func.strftime(fmt, IncidentRecord.report_date)

        rows = db.query(
            expr,
            IncidentRecord.lab,
            func.count(IncidentRecord.id)
        ).filter(
            IncidentRecord.report_date >= start_date,
            IncidentRecord.report_date != ""
        ).group_by(
            expr,
            IncidentRecord.lab
        ).order_by(expr).all()

        lab_set = set()
        data_map = {}
        for date_label, lab, cnt in rows:
            dl = clean_date_str(date_label)
            lab_name = lab or "未填写"
            lab_set.add(lab_name)
            data_map[(dl, lab_name)] = cnt

        now = datetime.now()
        start_dt = offset_fn(datetime.strptime(start_date, "%Y-%m-%d"))
        date_range = fill_date_range(start_dt, now, density)

        labs = sorted(lab_set)
        series = []
        for lab in labs:
            series.append({
                "name": lab,
                "data": [data_map.get((d, lab), 0) for d in date_range]
            })

        return {"labels": date_range, "series": series}
    finally:
        db.close()
