"""Azure Data Processing and Analytics System - main pipeline.

    raw container (CSV)  ->  clean  ->  analyse  ->  processed container

Run:
    python generate_sample_data.py   # one-time: put sample CSVs in the raw container
    python main.py
"""

import json
import logging
import sys
from datetime import datetime, timezone

import analytics
import processor
from config import load_settings
from storage import get_store

log = logging.getLogger("main")


def to_csv_bytes(df) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def run() -> None:
    settings = load_settings()
    store = get_store(settings)

    # 1. INGEST - find raw CSV files
    blobs = [b for b in store.list_blobs(settings.raw_container) if b.lower().endswith(".csv")]
    if not blobs:
        log.error("No CSV files found in container '%s'. Run generate_sample_data.py first.", settings.raw_container)
        sys.exit(1)
    raw = processor.load_raw(store, settings.raw_container, blobs)

    # 2. PROCESS - clean the data
    clean, stats = processor.clean(raw)

    # 3. ANALYSE
    summary_table = analytics.device_summary(clean)
    hourly = analytics.hourly_trend(clean)
    anomalies = analytics.detect_anomalies(clean, settings.temp_alert_c, settings.zscore_limit)
    summary = analytics.build_summary(clean, stats, anomalies)
    chart = analytics.make_chart(hourly)

    # 4. PUBLISH - write results to the processed container
    run_folder = "run_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    outputs = {
        "cleaned_telemetry.csv": to_csv_bytes(clean),
        "device_summary.csv": to_csv_bytes(summary_table),
        "hourly_trend.csv": to_csv_bytes(hourly),
        "anomalies.csv": to_csv_bytes(anomalies),
        "summary.json": json.dumps(summary, indent=2).encode("utf-8"),
        "hourly_temperature.png": chart,
    }
    for name, data in outputs.items():
        store.upload(settings.processed_container, f"{run_folder}/{name}", data)
        log.info("Uploaded %s/%s/%s", settings.processed_container, run_folder, name)

    log.info(
        "Done: %d clean readings, %d anomalies, results in '%s/%s'",
        len(clean),
        len(anomalies),
        settings.processed_container,
        run_folder,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    run()
