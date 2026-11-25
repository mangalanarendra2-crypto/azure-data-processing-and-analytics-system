# Azure Data Processing and Analytics System

A simple base project showing a cloud data pipeline on **Azure Blob Storage**:

```
 raw-data container      Python pipeline                 processed-data container
 (CSV telemetry)  --->  clean -> analyse -> chart  --->  cleaned CSV, summaries,
                                                         anomalies, summary.json, PNG
```

The sample data is IoT sensor telemetry (temperature and humidity from 3 devices).

It runs in two modes:

| Mode | When | What it uses |
|------|------|--------------|
| **Local** (default) | `AZURE_STORAGE_CONNECTION_STRING` is empty | a `local_storage/` folder that imitates blob containers |
| **Azure** | connection string is set | a real Azure Storage account |

## Project structure

```
azure_analytics/
├── config.py                # settings from environment variables / .env
├── storage.py               # LocalStore and AzureStore (same interface)
├── processor.py             # load raw CSVs + data cleaning
├── analytics.py             # summaries, anomaly detection, chart
├── main.py                  # the pipeline
├── generate_sample_data.py  # creates messy sample data in the raw container
├── requirements.txt
└── .env.example
```

## Quick start (local, no Azure account needed)

```bash
pip install -r requirements.txt
python generate_sample_data.py
python main.py
```

Results appear in `local_storage/processed-data/run_<timestamp>/`.

## Running against Azure

1. Create a Storage Account in the Azure Portal.
2. Copy its connection string (Storage account -> Access keys).
3. `cp .env.example .env` and paste the connection string into `.env`.
4. Run the same two commands. The containers `raw-data` and `processed-data`
   are created automatically.

## What the pipeline does

1. **Ingest** - lists every `.csv` in the raw container and loads them.
2. **Process** - normalises device names, parses timestamps, removes duplicates,
   missing values, and impossible readings (e.g. 999 sensor faults).
3. **Analyse** - per-device statistics, hourly trend, anomaly detection
   (temperature above `TEMP_ALERT_C` or z-score above `ZSCORE_LIMIT`), headline summary.
4. **Publish** - uploads six files to a new `run_<timestamp>/` folder:
   `cleaned_telemetry.csv`, `device_summary.csv`, `hourly_trend.csv`,
   `anomalies.csv`, `summary.json`, `hourly_temperature.png`.

## Ideas for taking it further

- Trigger `main.run()` automatically with an **Azure Function** (Blob trigger or Timer trigger).
- Load the cleaned data into **Azure SQL Database** or **Azure Data Lake**.
- Connect the processed container to **Power BI** for dashboards.
- Orchestrate the steps with **Azure Data Factory**.
