"""EHS LOTO Platform - Database Models"""
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, ForeignKey, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone
import os

Base = declarative_base()

# ── Site (场地) ──
class Site(Base):
    __tablename__ = "sites"
    id = Column(String, primary_key=True)      # "001", "002"
    name = Column(String, nullable=False)      # display name
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# ── Device (设备) ──
class Device(Base):
    __tablename__ = "devices"

    id = Column(String, primary_key=True)
    site = Column(String, default="001", index=True)  # 场地归属
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)          # LOT-001
    type = Column(String, nullable=False)          # electric/gas/water/mechanical/laser/other
    floor = Column(Integer, nullable=False)        # 1/2/3
    x = Column(Float, default=0)
    y = Column(Float, default=0)
    sub_system = Column(String, default="")
    energy_types = Column(JSON, default=list)      # ["电","水"]
    loto_steps = Column(JSON, default=list)        # LOTO操作步骤
    location = Column(String, default="")
    is_locked = Column(Boolean, default=False)
    locked_breaker_ids = Column(JSON, default=list)
    is_affected = Column(Boolean, default=False)
    affected_by_list = Column(JSON, default=list)
    person = Column(String, default="")            # 负责人
    breakers = Column(JSON, default=list)          # 空开列表（电柜设备）
    extra = Column(JSON, default=dict)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        """Export as camelCase for frontend compatibility"""
        mapping = {
            'sub_system': 'subSystem', 'energy_types': 'energyTypes',
            'loto_steps': 'lotoSteps', 'is_locked': 'isLocked',
            'locked_breaker_ids': 'lockedBreakerIds', 'is_affected': 'isAffected',
            'affected_by_list': 'affectedByList'
        }
        result = {}
        for c in self.__table__.columns:
            v = getattr(self, c.name)
            key = mapping.get(c.name, c.name)
            result[key] = v
        return result


# ── Connection (连接关系) ──
class Connection(Base):
    __tablename__ = "connections"

    id = Column(String, primary_key=True)
    site = Column(String, default="001", index=True)  # 场地归属
    from_device_id = Column(String, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    to_device_id = Column(String, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False)
    from_floor = Column(Integer, nullable=False)
    to_floor = Column(Integer, nullable=False)
    label = Column(String, default="")
    from_breaker_id = Column(String, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "from": self.from_device_id,
            "to": self.to_device_id,
            "fromFloor": self.from_floor,
            "toFloor": self.to_floor,
            "label": self.label,
            "fromBreakerId": self.from_breaker_id,
        }


# ── DB Setup ──
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/loto.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    # 迁移：添加 from_breaker_id 列（如果不存在）
    from sqlalchemy import inspect
    inspector = inspect(engine)
    if 'connections' in inspector.get_table_names():
        cols = [c['name'] for c in inspector.get_columns('connections')]
        if 'from_breaker_id' not in cols:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text('ALTER TABLE connections ADD COLUMN from_breaker_id VARCHAR'))
                conn.commit()
    # Seed default site
    db = SessionLocal()
    try:
        if not db.query(Site).first():
            db.add(Site(id="001", name="场地 001"))
            db.commit()
    finally:
        db.close()
