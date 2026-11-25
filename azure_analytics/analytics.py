"""Analytics: summaries, anomaly detection and a chart."""

import io
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def device_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per device with basic statistics."""
    out = df.groupby("device_id").agg(
        readings=("temperature_c", "count"),
        avg_temp_c=("temperature_c", "mean"),
        min_temp_c=("temperature_c", "min"),
        max_temp_c=("temperature_c", "max"),
        avg_humidity_pct=("humidity_pct", "mean"),
    )
    return out.round(2).reset_index()


def hourly_trend(df: pd.DataFrame) -> pd.DataFrame:
    """Average temperature and humidity per device per hour."""
    out = df.groupby(["hour", "device_id"], as_index=False).agg(
        avg_temp_c=("temperature_c", "mean"), avg_humidity_pct=("humidity_pct", "mean")
    )
    out[["avg_temp_c", "avg_humidity_pct"]] = out[["avg_temp_c", "avg_humidity_pct"]].round(2)
    return out


def detect_anomalies(df: pd.DataFrame, temp_alert_c: float, zscore_limit: float) -> pd.DataFrame:
    """Flag readings that are too hot or statistically unusual for their device."""
    grouped = df.groupby("device_id")["temperature_c"]
    zscore = (df["temperature_c"] - grouped.transform("mean")) / grouped.transform("std")

    too_hot = df["temperature_c"] > temp_alert_c
    outlier = zscore.abs() > zscore_limit

    out = df[too_hot | outlier].copy()
    out["zscore"] = zscore[out.index].round(2)
    out["reason"] = np.where(too_hot[out.index], "over temperature limit", "statistical outlier")
    return out[["device_id", "timestamp", "temperature_c", "humidity_pct", "zscore", "reason"]]


def build_summary(df: pd.DataFrame, stats: dict, anomalies: pd.DataFrame) -> dict:
    """Headline numbers for the run, saved as summary.json."""
    hottest = df.loc[df["temperature_c"].idxmax()]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_quality": {k: int(v) for k, v in stats.items()},
        "clean_readings": int(len(df)),
        "devices": sorted(df["device_id"].unique().tolist()),
        "period_start": df["timestamp"].min().isoformat(),
        "period_end": df["timestamp"].max().isoformat(),
        "overall_avg_temp_c": round(float(df["temperature_c"].mean()), 2),
        "overall_avg_humidity_pct": round(float(df["humidity_pct"].mean()), 2),
        "hottest_reading": {
            "device_id": hottest["device_id"],
            "temperature_c": float(hottest["temperature_c"]),
            "timestamp": hottest["timestamp"].isoformat(),
        },
        "anomaly_count": int(len(anomalies)),
    }


def make_chart(hourly: pd.DataFrame) -> bytes:
    """Line chart of hourly average temperature per device; returns PNG bytes."""
    pivot = hourly.pivot(index="hour", columns="device_id", values="avg_temp_c")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for device in pivot.columns:
        ax.plot(pivot.index, pivot[device], marker="o", markersize=3, label=device)
    ax.set_title("Hourly Average Temperature by Device")
    ax.set_ylabel("Temperature (°C)")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    return buffer.getvalue()
