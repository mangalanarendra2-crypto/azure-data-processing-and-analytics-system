"""Create sample IoT temperature/humidity data and upload it to the raw container.

Works in local mode and with real Azure Blob Storage (uses the same storage layer).
The data deliberately contains problems the pipeline must handle:
duplicates, missing values, sensor errors (999), messy device names,
an unparseable timestamp, and a few genuine temperature spikes.
"""

import logging

import numpy as np
import pandas as pd

from config import load_settings
from storage import get_store


def make_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    times = pd.date_range("2026-11-24 00:00", periods=144, freq="10min")  # 24 hours
    devices = {"SENSOR-01": 0.0, "SENSOR-02": 1.5, "SENSOR-03": -1.0}

    frames = []
    for device, offset in devices.items():
        daily_wave = 6 * np.sin((times.hour + times.minute / 60 - 8) / 24 * 2 * np.pi)
        frames.append(
            pd.DataFrame(
                {
                    "device_id": device,
                    "timestamp": times.strftime("%Y-%m-%d %H:%M:%S"),
                    "temperature_c": (22 + offset + daily_wave + rng.normal(0, 0.6, len(times))).round(2),
                    "humidity_pct": (55 - daily_wave * 1.5 + rng.normal(0, 2, len(times))).round(1),
                }
            )
        )
    df = pd.concat(frames, ignore_index=True)

    # --- inject realistic problems ---
    df.loc[[200, 201, 202], "temperature_c"] = [38.4, 40.1, 39.2]  # real spikes (SENSOR-02)
    df.loc[[10, 300], "temperature_c"] = 999  # sensor faults
    df.loc[[25, 60, 330], "humidity_pct"] = np.nan  # missing humidity
    df.loc[[5, 150], "device_id"] = [" sensor-01 ", "sensor-03"]  # messy names
    df.loc[90, "timestamp"] = "not-a-time"  # bad timestamp
    df = pd.concat([df, df.iloc[[40, 41, 220, 221]]], ignore_index=True)  # duplicates
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    settings = load_settings()
    store = get_store(settings)

    df = make_data()
    # Split into two files to mimic data arriving in batches
    parts = {"telemetry_part1.csv": df.iloc[: len(df) // 2], "telemetry_part2.csv": df.iloc[len(df) // 2 :]}
    for name, part in parts.items():
        store.upload(settings.raw_container, name, part.to_csv(index=False).encode("utf-8"))
        logging.info("Uploaded %s/%s (%d rows)", settings.raw_container, name, len(part))


if __name__ == "__main__":
    main()
