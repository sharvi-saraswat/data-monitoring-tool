"""Headless monitor for scheduling (cron / Task Scheduler).
Usage: python monitor_cli.py data/sample_dirty.csv [timestamp_column]"""
import sys
from monitor import checks, storage, alerts, ingest

path = sys.argv[1]
cfg = {"timestamp_column": sys.argv[2]} if len(sys.argv) > 2 else {}
df = ingest.load_file(path, path)
res = checks.run_all_checks(df, storage.load_baseline(), cfg)
score = checks.quality_score(res)
storage.save_run(path, df, res, score)
alerted = alerts.send_alerts(path, res, score)
print(f"{path}: score {score}/100 | alert sent/logged: {alerted}")
