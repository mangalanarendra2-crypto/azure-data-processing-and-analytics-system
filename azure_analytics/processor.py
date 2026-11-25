"""Data processing: load raw CSV blobs and clean them."""

import io
import logging

import pandas as pd

log = logging.getLogger(__name__)

REQUIRED = ["device_id", "timestamp", "temperature_c", "humidity_pct"]

# Physically plausible sensor ranges; anything outside is a sensor error
TEMP_RANGE = (-40.0, 85.0)
HUMIDITY_RANGE = (0.0, 100.0)


def load_raw(store, container: str, blob_names: list[str]) -> pd.DataFrame:
    """Download every CSV blob and combine them into one DataFrame."""
    frames = []
    for name in blob_names:
        df = pd.read_csv(io.BytesIO(store.download(container, name)), dtype=str)
        df["source_file"] = name
        frames.append(df)
        log.info("Loaded %s (%d rows)", name, len(df))
    return pd.concat(frames, ignore_index=True)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Standardise, validate and de-duplicate telemetry readings.

    Returns the clean DataFrame plus a dict of data-quality counts.
    """
    stats = {"rows_in": len(df)}
    df = df.copy()

    # Standardise types
    df["device_id"] = df["device_id"].str.strip().str.upper()
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["temperature_c"] = pd.to_numeric(df["temperature_c"], errors="coerce")
    df["humidity_pct"] = pd.to_numeric(df["humidity_pct"], errors="coerce")

    # Remove duplicate readings
    before = len(df)
    df = df.drop_duplicates(subset=["device_id", "timestamp"], keep="first")
    stats["duplicates_removed"] = before - len(df)

    # Remove rows with missing / unparseable values
    before = len(df)
    df = df.dropna(subset=REQUIRED)
    stats["missing_removed"] = before - len(df)

    # Remove impossible values (sensor faults such as 999)
    before = len(df)
    valid = df["temperature_c"].between(*TEMP_RANGE) & df["humidity_pct"].between(*HUMIDITY_RANGE)
    df = df[valid]
    stats["out_of_range_removed"] = before - len(df)

    # Helper columns for analytics
    df["hour"] = df["timestamp"].dt.floor("h")
    df = df.sort_values(["device_id", "timestamp"]).reset_index(drop=True)

    stats["rows_out"] = len(df)
    log.info("Cleaning done: %s", stats)
    return df, stats
