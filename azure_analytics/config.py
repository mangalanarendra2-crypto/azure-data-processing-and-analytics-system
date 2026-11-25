"""Settings for the Azure Data Processing and Analytics System.

Everything is read from environment variables (or a .env file) so no secrets
live in the code. If AZURE_STORAGE_CONNECTION_STRING is not set, the project
runs in LOCAL mode using a folder that imitates Azure Blob Storage.
"""

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional
    pass


@dataclass(frozen=True)
class Settings:
    connection_string: str | None  # Azure Storage account connection string
    raw_container: str  # where raw CSV files arrive
    processed_container: str  # where results are written
    local_root: Path  # used only in local mode
    temp_alert_c: float  # temperatures above this are flagged
    zscore_limit: float  # statistical outlier threshold


def load_settings() -> Settings:
    return Settings(
        connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING") or None,
        raw_container=os.getenv("RAW_CONTAINER", "raw-data"),
        processed_container=os.getenv("PROCESSED_CONTAINER", "processed-data"),
        local_root=Path(os.getenv("LOCAL_STORAGE_ROOT", "local_storage")),
        temp_alert_c=float(os.getenv("TEMP_ALERT_C", "35")),
        zscore_limit=float(os.getenv("ZSCORE_LIMIT", "3")),
    )
