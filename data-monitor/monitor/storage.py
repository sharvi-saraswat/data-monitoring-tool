"""MEMBER 1 - Storage layer: SQLite history of runs, issues and baseline."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parent.parent / "data" / "monitor.db"


def _conn():
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS runs(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, source TEXT,
        rows INTEGER, cols INTEGER, score INTEGER, fails INTEGER, warns INTEGER);
    CREATE TABLE IF NOT EXISTS issues(
        run_id INTEGER, chk TEXT, col TEXT, value REAL, status TEXT, detail TEXT);
    CREATE TABLE IF NOT EXISTS baseline(id INTEGER PRIMARY KEY, ts TEXT, payload TEXT);
    """)
    return c


def save_run(source, df, results, score):
    fails = sum(r["status"] == "FAIL" for r in results)
    warns = sum(r["status"] == "WARN" for r in results)
    c = _conn()
    with c:
        cur = c.execute("INSERT INTO runs(ts,source,rows,cols,score,fails,warns) "
                        "VALUES(?,?,?,?,?,?,?)",
                        (datetime.now().isoformat(timespec="seconds"), source,
                         len(df), df.shape[1], score, fails, warns))
        rid = cur.lastrowid
        c.executemany("INSERT INTO issues VALUES(?,?,?,?,?,?)",
                      [(rid, r["check"], r["column"], r["value"],
                        r["status"], r["detail"]) for r in results])
    c.close()
    return rid


def load_runs(limit=200):
    c = _conn()
    df = pd.read_sql("SELECT * FROM runs ORDER BY id DESC LIMIT ?", c, params=(limit,))
    c.close()
    return df


def load_issues(run_id):
    c = _conn()
    df = pd.read_sql("SELECT * FROM issues WHERE run_id=?", c, params=(int(run_id),))
    c.close()
    return df


def save_baseline(payload):
    c = _conn()
    with c:
        c.execute("DELETE FROM baseline")
        c.execute("INSERT INTO baseline(ts,payload) VALUES(?,?)",
                  (datetime.now().isoformat(timespec="seconds"), json.dumps(payload)))
    c.close()


def load_baseline():
    c = _conn()
    row = c.execute("SELECT payload FROM baseline ORDER BY id DESC LIMIT 1").fetchone()
    c.close()
    return json.loads(row[0]) if row else None
