from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ─── Database ─────────────────────────────────────────
    postgres_dsn: str = "postgresql+asyncpg://agri:localpassword@localhost:5432/agri_engine"
    redis_url: str = "redis://localhost:6379/0"

    # ─── External APIs ────────────────────────────────────
    bhuvan_api_key: str = ""
    imd_api_token: str = ""
    nasa_earthdata_token: str = ""
    fasal_bima_api_key: str = ""

    # ─── UPI Payout ───────────────────────────────────────
    upi_merchant_id: str = ""
    upi_api_key: str = ""
    upi_api_base_url: str = "https://api.razorpay.com/v1"

    # ─── Encryption ───────────────────────────────────────
    fernet_encryption_key: str = ""

    # ─── Processing ───────────────────────────────────────
    dask_scheduler_address: str = ""          # empty = LocalCluster
    spark_master_url: str = "spark://localhost:7077"
    pilot_state_code: str = "MH"             # Maharashtra

    # ─── Payout Limits ────────────────────────────────────
    max_payout_per_event_inr: float = 25000.0

    # ─── Trigger Thresholds ───────────────────────────────
    ndvi_change_threshold: float = -0.30      # 30% drop from baseline
    flood_rainfall_48h_mm: float = 200.0
    drought_rainfall_14d_mm: float = 20.0
    soil_vwc_threshold: float = 15.0          # % volumetric water content

    # ─── Pipeline Timing ──────────────────────────────────
    payout_cooldown_days: int = 30            # min days between same rule on same farm
    upi_poll_max_hours: int = 4               # poll PENDING payouts for this long
    upi_poll_interval_minutes: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
