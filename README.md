# Data Monitoring Tool

Monitors datasets (CSV / Excel / JSON) for quality problems, schema changes and
distribution drift, stores every run in SQLite, raises alerts, and shows everything
in a Streamlit dashboard.

## Run it
```bash
pip install -r requirements.txt
python generate_sample_data.py      # creates sample clean + dirty data
streamlit run app.py
```
Demo flow: pick **Sample (clean)** -> *Set as baseline* -> pick **Sample (with issues)**
-> choose timestamp column `order_date` -> *Run monitoring* -> see FAIL/WARN, history tab.

Headless / scheduled: `python monitor_cli.py data/sample_dirty.csv order_date`
Email alerts (optional): set `SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_TO`.

## Checks
Missing values - duplicate rows - IQR outliers - schema change - drift (PSI) - freshness.
Quality score = 100 - 10 per FAIL - 3 per WARN.

## Team roles
| Member | Role | Files | Deliverables |
|---|---|---|---|
| 1 | Data & Storage Engineer | `monitor/ingest.py`, `monitor/storage.py`, `generate_sample_data.py` | File loaders (CSV/Excel/JSON), SQLite schema (runs, issues, baseline), sample datasets, add DB/API/S3 connectors |
| 2 | Monitoring & Alerts Engineer | `monitor/checks.py`, `monitor/alerts.py`, `monitor_cli.py`, `tests/` | All quality checks, thresholds, scoring, email/log alerts, unit tests, scheduling |
| 3 | Dashboard, Integration & Docs Lead | `app.py`, `README.md`, deployment | Streamlit UI, charts, history view, report download, Streamlit Cloud/Docker deploy, final report + PPT + demo |

Shared: Git branches per member, weekly merge, final demo rehearsal together.
