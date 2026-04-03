import uuid
from datetime import datetime, date
from enum import Enum

from geoalchemy2 import Geometry
from sqlalchemy import (
    UUID, Boolean, DateTime, Date, Enum as SAEnum,
    ForeignKey, Numeric, String, Text, Integer, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class PolicyStatus(str, Enum):
    active = "active"
    expired = "expired"
    suspended = "suspended"


class PayoutStatus(str, Enum):
    queued = "queued"
    pending = "pending"
    success = "success"
    failed = "failed"
    manually_cancelled = "manually_cancelled"


class Farmer(Base):
    __tablename__ = "farmers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Aadhaar Act compliance: never store plaintext — SHA-256 + salt only
    aadhaar_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    state_code: Mapped[str] = mapped_column(String(5), nullable=False)
    district_code: Mapped[str] = mapped_column(String(10), nullable=False)
    # UPI ID and bank account encrypted at rest (Fernet symmetric encryption)
    upi_id_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_account_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    bank_ifsc: Mapped[str | None] = mapped_column(String(15), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    farms: Mapped[list["Farm"]] = relationship("Farm", back_populates="farmer")


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farmers.id"), nullable=False)
    area_hectares: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    # PostGIS geometry — stored as WGS84 (EPSG:4326)
    polygon: Mapped[str] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    centroid: Mapped[str] = mapped_column(Geometry("POINT", srid=4326), nullable=True)
    state_code: Mapped[str] = mapped_column(String(5), nullable=False, index=True)
    district_code: Mapped[str] = mapped_column(String(10), nullable=False)
    taluka: Mapped[str | None] = mapped_column(String(100), nullable=True)
    soil_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    crop_type_current_season: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    farmer: Mapped["Farmer"] = relationship("Farmer", back_populates="farms")
    policies: Mapped[list["Policy"]] = relationship("Policy", back_populates="farm")


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farms.id"), nullable=False)
    farmer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("farmers.id"), nullable=False)
    policy_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    coverage_start: Mapped[date] = mapped_column(Date, nullable=False)
    coverage_end: Mapped[date] = mapped_column(Date, nullable=False)
    insured_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    sum_insured_inr: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    premium_paid_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    # Payout percentages per tier
    tier_1_payout_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.40)   # 40%
    tier_2_payout_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.25)   # 25%
    tier_3_payout_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.15)   # 15%
    status: Mapped[PolicyStatus] = mapped_column(SAEnum(PolicyStatus), default=PolicyStatus.active)
    fasal_bima_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    farm: Mapped["Farm"] = relationship("Farm", back_populates="policies")


class SensorReading(Base):
    """TimescaleDB hypertable — partitioned by timestamp weekly."""
    __tablename__ = "sensor_readings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    station_id: Mapped[str] = mapped_column(String(50), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rainfall_mm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    temp_celsius: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    humidity_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    wind_kmh: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    # Soil sensor specific
    vwc_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    depth_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)   # imd | soil_iot | modis


class FarmDailyStat(Base):
    """TimescaleDB hypertable — per-farm daily stats from satellite + weather processing."""
    __tablename__ = "farm_daily_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    stat_date: Mapped[date] = mapped_column(Date, nullable=False)
    mean_ndvi: Mapped[float | None] = mapped_column(Numeric(6, 4), nullable=True)
    ndvi_change_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), nullable=True)
    rainfall_48h_mm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    rainfall_14d_mm: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    mean_vwc_percent: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    modis_flood_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    modis_fire_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    data_source_ndvi: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PayoutRecord(Base):
    """Immutable audit ledger — every payout fully traceable to source data."""
    __tablename__ = "payout_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    farmer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    policy_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_event_id: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    payout_inr: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PayoutStatus] = mapped_column(SAEnum(PayoutStatus), default=PayoutStatus.queued)
    upi_reference_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    utr_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # S3 URL or local path to satellite image / sensor log that triggered this payout
    evidence_artifact_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
