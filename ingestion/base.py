from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path


class AbstractIngester(ABC):
    """
    All data source ingesters follow this protocol:
    fetch → validate → store

    This makes swapping schedulers (Celery Beat → Airflow) a config change only.
    """

    source_id: str

    @abstractmethod
    def fetch(self, region: str, fetch_date: date) -> Path:
        """Download data for region + date. Returns local file path."""

    @abstractmethod
    def validate(self, artifact: Path) -> bool:
        """Validate downloaded artifact (checksum, schema, value ranges)."""

    @abstractmethod
    def store(self, artifact: Path) -> str:
        """Store artifact to S3 or local data dir. Returns storage key/path."""

    def run(self, region: str, fetch_date: date) -> str:
        """Orchestrate fetch → validate → store. Returns storage location."""
        artifact = self.fetch(region, fetch_date)
        if not self.validate(artifact):
            raise ValueError(f"{self.source_id}: validation failed for {artifact}")
        return self.store(artifact)
