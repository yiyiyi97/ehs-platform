"""异常事件管理 - 数据库模型"""
from sqlalchemy import Column, String, Integer, Text, DateTime, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
import os

Base = declarative_base()
DATABASE_URL = os.getenv("INCIDENT_DATABASE_URL", "sqlite:///./data/incident.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)


class IncidentRecord(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_no = Column(String, nullable=False, index=True)
    incident_type = Column(String, default="")
    event_level = Column(String, default="")
    lab = Column(String, default="")
    version = Column(String, default="")
    subsystem = Column(String, default="")
    device_name = Column(String, default="")
    description = Column(Text, default="")
    review_report_path = Column(String, default="")
    status = Column(String, default="待复盘")
    reporter = Column(String, default="")
    report_date = Column(String, default="")
    review_date = Column(String, default="")
    reviewer = Column(String, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            if isinstance(v, datetime):
                v = v.isoformat()
            result[c.name] = v
        return result


class Option(Base):
    __tablename__ = "incident_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field_name = Column(String, nullable=False, index=True)
    value = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed default options
        if db.query(Option).count() == 0:
            defaults = [
                ("event_level", "High"), ("event_level", "Medium"), ("event_level", "Low"),
                ("incident_type", "电气"), ("incident_type", "水"), ("incident_type", "气体"),
                ("incident_type", "机械"), ("incident_type", "激光"), ("incident_type", "其他"),
                ("lab", "L1"), ("lab", "L2"), ("lab", "L3"),
                ("version", "V1"), ("version", "V2"), ("version", "V3"),
                ("subsystem", "扩散"), ("subsystem", "薄膜"), ("subsystem", "光刻"),
                ("subsystem", "蚀刻"), ("subsystem", "离子注入"), ("subsystem", "其他"),
                ("device_name", "设备A"), ("device_name", "设备B"), ("device_name", "设备C"),
                ("status", "待复盘"), ("status", "已复盘"), ("status", "措施已落实"),
            ]
            for fn, val in defaults:
                db.add(Option(field_name=fn, value=val))
            db.commit()
    finally:
        db.close()
