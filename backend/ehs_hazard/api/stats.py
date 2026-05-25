"""BI 数据分析 API"""
from fastapi import APIRouter, Depends
from ehs_hazard.models import SessionLocal, HazardRecord
from ehs_hazard.api.auth import get_current_user, get_current_user_optional
from sqlalchemy import func
from datetime import datetime, timedelta
import calendar

router = APIRouter()

TREND_DENSITY_MAP = {
    "day":   ("%Y-%m-%d", lambda d: d, 1),
    "week":  ("%Y-%W",    lambda d: d - timedelta(days=d.weekday()), 7),
    "month": ("%Y-%m",    lambda d: d.replace(day=1), 0),
}


def get_density_sql(col, density):
    """按密度返回 SQLAlchemy 分组表达式和格式化函数"""
    fmt, offset_fn, _ = TREND_DENSITY_MAP[density]
    return func.strftime(fmt, col), offset_fn


def fill_date_range(start, end, density):
    """生成连续时间轴（天/周/月）"""
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
    """统一日期格式：去掉时间部分"""
    if val is None:
        return ""
    s = str(val)[:10]  # "2026-04-21 00:00:00" → "2026-04-21"
    return s


@router.get("/aggregate")
def aggregate(group_by: str = "risk_level", metric: str = "count", filters: str = "", user=Depends(get_current_user_optional)):
    import json
    db = SessionLocal()
    try:
        valid_fields = {
            "risk_level", "risk_type", "lab", "floor", "subsystem", "version",
            "status", "check_type", "equipment_phase", "reporter",
            "responsible_person", "equipment", "responsible_dept"
        }
        if group_by not in valid_fields:
            return {"labels": [], "values": []}

        # close_days 是计算字段，特殊处理
        if group_by == "close_days":
            rows = db.query(
                case(
                    (func.julianday(HazardRecord.close_date) - func.julianday(HazardRecord.report_date) < 0, None),
                    else_=func.round(func.julianday(HazardRecord.close_date) - func.julianday(HazardRecord.report_date))
                ).label("days"),
                func.count(HazardRecord.id)
            ).filter(HazardRecord.close_date != "", HazardRecord.close_date != None,
                     HazardRecord.report_date != "", HazardRecord.report_date != None)\
            .group_by("days").order_by("days").all()
            labels = [f"{int(r[0]) if r[0] else '?'}天" for r in rows if r[0] is not None]
            values = [r[1] for r in rows if r[0] is not None]
            return {"labels": labels, "values": values}

        q = db.query(
            getattr(HazardRecord, group_by),
            func.count(HazardRecord.id)
        )
        if filters:
            try:
                flt = json.loads(filters)
                for k, v in flt.items():
                    if v and k in valid_fields.union({"floor","version"}):
                        col = getattr(HazardRecord, k, None)
                        if col is not None:
                            q = q.filter(col == v)
            except:
                pass

        rows = q.group_by(getattr(HazardRecord, group_by)).order_by(func.count(HazardRecord.id).desc()).all()
        labels = [r[0] or "未填写" for r in rows]
        values = [r[1] for r in rows]
        return {"labels": labels, "values": values}
    finally:
        db.close()


@router.get("/summary")
def summary(user=Depends(get_current_user_optional)):
    db = SessionLocal()
    try:
        total = db.query(HazardRecord).count()
        by_status = dict(db.query(HazardRecord.status, func.count(HazardRecord.id)).group_by(HazardRecord.status).all())
        by_level = dict(db.query(HazardRecord.risk_level, func.count(HazardRecord.id)).group_by(HazardRecord.risk_level).all())
        by_type = dict(db.query(HazardRecord.risk_type, func.count(HazardRecord.id)).group_by(HazardRecord.risk_type).all())
        overdue = db.query(HazardRecord).filter(
            HazardRecord.status == "open",
            HazardRecord.expected_close_date < func.date("now"),
            HazardRecord.expected_close_date != ""
        ).count()
        closed = by_status.get("closed", 0)
        closeRate = round(closed / total * 100, 1) if total > 0 else 0
        return {
            "total": total,
            "by_status": by_status,
            "by_level": by_level,
            "by_type": by_type,
            "overdue": overdue,
            "closed": closed,
            "closeRate": closeRate
        }
    finally:
        db.close()


@router.get("/trend")
def trend(group_by: str = "report_date", days: int = 30, density: str = "day", user=Depends(get_current_user_optional)):
    """趋势数据（折线图）

    density: day / week / month — X 轴密度
    """
    db = SessionLocal()
    try:
        if group_by == "report_date":
            col = HazardRecord.report_date
        elif group_by == "close_date":
            col = HazardRecord.close_date
        else:
            col = HazardRecord.report_date

        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        fmt, offset_fn = get_density_sql(col, density)
        expr = func.strftime(fmt, col)

        rows = db.query(expr, func.count(HazardRecord.id)).filter(
            col >= start_date
        ).group_by(expr).order_by(expr).all()

        # 填充完整时间轴
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
def cross_analysis(x_field: str = "risk_level", y_field: str = "risk_type", user=Depends(get_current_user)):
    db = SessionLocal()
    try:
        valid = {"risk_level", "risk_type", "lab", "floor", "subsystem", "version", "status", "check_type", "equipment_phase"}
        if x_field not in valid or y_field not in valid:
            return {"labels": [], "series": []}

        rows = db.query(
            getattr(HazardRecord, x_field),
            getattr(HazardRecord, y_field),
            func.count(HazardRecord.id)
        ).group_by(
            getattr(HazardRecord, x_field),
            getattr(HazardRecord, y_field)
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
    """按实验室分组的隐患趋势（堆叠折线图用）

    density: day / week / month — X 轴密度
    """
    db = SessionLocal()
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        fmt, offset_fn = get_density_sql(HazardRecord.report_date, density)
        expr = func.strftime(fmt, HazardRecord.report_date)

        rows = db.query(
            expr,
            HazardRecord.lab,
            func.count(HazardRecord.id)
        ).filter(
            HazardRecord.report_date >= start_date,
            HazardRecord.report_date != ""
        ).group_by(
            expr,
            HazardRecord.lab
        ).order_by(expr).all()

        # 收集数据
        lab_set = set()
        data_map = {}
        for date_label, lab, cnt in rows:
            dl = clean_date_str(date_label)
            lab_name = lab or "未填写"
            lab_set.add(lab_name)
            data_map[(dl, lab_name)] = cnt

        # 生成完整时间轴
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
