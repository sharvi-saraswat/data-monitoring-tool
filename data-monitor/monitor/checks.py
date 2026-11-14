"""MEMBER 2 - Monitoring engine: all data-quality checks live here."""
import numpy as np
import pandas as pd

DEFAULT_CONFIG = {
    "missing_warn": 0.05,      # >5% nulls in a column -> WARN
    "missing_fail": 0.20,      # >20% nulls -> FAIL
    "duplicate_warn": 0.01,    # >1% duplicate rows -> WARN
    "duplicate_fail": 0.05,
    "outlier_warn": 0.02,      # >2% IQR outliers -> WARN
    "outlier_fail": 0.10,
    "psi_warn": 0.10,          # distribution drift (PSI)
    "psi_fail": 0.25,
    "freshness_hours": 24,     # newest timestamp older than this -> FAIL
    "timestamp_column": None,  # e.g. "order_date"
}


def _status(value, warn, fail):
    if value >= fail:
        return "FAIL"
    if value >= warn:
        return "WARN"
    return "PASS"


def _row(check, column, value, status, detail=""):
    return {"check": check, "column": column, "value": round(float(value), 4),
            "status": status, "detail": detail}


def check_missing(df, cfg):
    out = []
    for col in df.columns:
        r = df[col].isna().mean()
        out.append(_row("missing_values", col, r,
                        _status(r, cfg["missing_warn"], cfg["missing_fail"]),
                        f"{r:.1%} null"))
    return out


def check_duplicates(df, cfg):
    r = df.duplicated().mean() if len(df) else 0
    return [_row("duplicate_rows", "*", r,
                 _status(r, cfg["duplicate_warn"], cfg["duplicate_fail"]),
                 f"{int(df.duplicated().sum())} duplicate rows")]


def check_outliers(df, cfg):
    out = []
    for col in df.select_dtypes(include="number").columns:
        s = df[col].dropna()
        if len(s) < 10:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        r = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).mean() if iqr else 0
        out.append(_row("outliers_iqr", col, r,
                        _status(r, cfg["outlier_warn"], cfg["outlier_fail"]),
                        f"{r:.1%} outside IQR fences"))
    return out


def check_schema(df, baseline):
    """Compare columns and dtypes with the saved baseline."""
    if baseline is None:
        return []
    out, base = [], baseline["schema"]
    cur = {c: str(t) for c, t in df.dtypes.items()}
    for c in base:
        if c not in cur:
            out.append(_row("schema", c, 1, "FAIL", "column missing"))
        elif cur[c] != base[c]:
            out.append(_row("schema", c, 1, "WARN", f"type {base[c]} -> {cur[c]}"))
    for c in cur:
        if c not in base:
            out.append(_row("schema", c, 1, "WARN", "new column"))
    if not out:
        out.append(_row("schema", "*", 0, "PASS", "matches baseline"))
    return out


def _psi(expected, actual, bins=10):
    edges = np.unique(np.quantile(expected, np.linspace(0, 1, bins + 1)))
    if len(edges) < 3:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    e = np.histogram(expected, edges)[0] / len(expected)
    a = np.histogram(actual, edges)[0] / len(actual)
    e, a = np.clip(e, 1e-4, None), np.clip(a, 1e-4, None)
    return float(np.sum((a - e) * np.log(a / e)))


def check_drift(df, baseline, cfg):
    if baseline is None:
        return []
    out = []
    for col, ref in baseline["numeric_samples"].items():
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            cur = df[col].dropna()
            if len(cur) >= 10 and len(ref) >= 10:
                p = _psi(np.array(ref), cur.to_numpy())
                out.append(_row("drift_psi", col, p,
                                _status(p, cfg["psi_warn"], cfg["psi_fail"]),
                                f"PSI={p:.3f}"))
    return out


def check_freshness(df, cfg):
    col = cfg.get("timestamp_column")
    if not col or col not in df.columns:
        return []
    ts = pd.to_datetime(df[col], errors="coerce").max()
    if pd.isna(ts):
        return [_row("freshness", col, 0, "FAIL", "no valid timestamps")]
    age_h = (pd.Timestamp.now() - ts).total_seconds() / 3600
    st = "FAIL" if age_h > cfg["freshness_hours"] else "PASS"
    return [_row("freshness", col, age_h, st, f"newest record {age_h:.1f}h old")]


def build_baseline(df):
    """Snapshot of a 'good' dataset used for schema/drift comparison."""
    samples = {c: df[c].dropna().sample(min(2000, int(df[c].notna().sum())),
                                        random_state=1).tolist()
               for c in df.select_dtypes(include="number").columns}
    return {"schema": {c: str(t) for c, t in df.dtypes.items()},
            "numeric_samples": samples}


def run_all_checks(df, baseline=None, cfg=None):
    cfg = {**DEFAULT_CONFIG, **(cfg or {})}
    return (check_missing(df, cfg) + check_duplicates(df, cfg)
            + check_outliers(df, cfg) + check_schema(df, baseline)
            + check_drift(df, baseline, cfg) + check_freshness(df, cfg))


def quality_score(results):
    """100 minus 10 per FAIL and 3 per WARN (floor 0)."""
    fails = sum(r["status"] == "FAIL" for r in results)
    warns = sum(r["status"] == "WARN" for r in results)
    return max(0, 100 - 10 * fails - 3 * warns)
