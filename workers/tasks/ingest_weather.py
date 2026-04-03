import structlog
from datetime import date

from workers.celery_app import celery_app
from ingestion.imd_weather import fetch_station_readings

log = structlog.get_logger()

MAHARASHTRA_DISTRICTS = [
    "MH001", "MH002", "MH003", "MH004", "MH005",
    "MH006", "MH007", "MH008", "MH009", "MH010",
]


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def fetch_imd_maharashtra(self):
    """Fetch IMD weather readings for all Maharashtra districts."""
    today = date.today()
    total_records = 0

    for district_code in MAHARASHTRA_DISTRICTS:
        try:
            readings = fetch_station_readings(district_code, today)
            # TODO: bulk insert readings to TimescaleDB sensor_readings table
            total_records += len(readings)
            log.info("ingest.imd.district_done", district=district_code, records=len(readings))
        except Exception as exc:
            log.error("ingest.imd.district_failed", district=district_code, error=str(exc))
            self.retry(exc=exc)

    log.info("ingest.imd.complete", total_records=total_records, date=str(today))
    return {"total_records": total_records, "date": str(today)}
