"""MEMBER 3 - Streamlit dashboard."""
import time
import pandas as pd
from pathlib import Path
BASE = Path(__file__).resolve().parent
import streamlit as st
from monitor import checks, storage, alerts, ingest

st.set_page_config(page_title="Data Monitoring Tool", page_icon="📊", layout="wide")
st.title("📊 Data Monitoring Tool")
st.caption("Data quality, schema and drift monitoring with history and alerts")

# ---------- Sidebar ----------
st.sidebar.header("1. Data source")
src = st.sidebar.radio("Source", ["Upload file", "Sample (clean)", "Sample (with issues)", "Folder path"])
df, name = None, None
if src == "Upload file":
    up = st.sidebar.file_uploader("CSV / Excel / JSON", type=["csv", "xlsx", "xls", "json"])
    if up:
        df, name = ingest.load_file(up, up.name), up.name
elif src.startswith("Sample"):
    f = str(BASE / "data" / ("sample_clean.csv" if "clean" in src else "sample_dirty.csv"))
    try:
        df, name = pd.read_csv(f), f
    except FileNotFoundError:
        st.sidebar.error("Run: python generate_sample_data.py")
else:
    p = st.sidebar.text_input("File path", str(BASE / "data" / "sample_dirty.csv"))
    try:
        df, name = ingest.load_file(p, p), p
    except Exception as e:
        st.sidebar.warning(str(e))

st.sidebar.header("2. Thresholds")
cfg = {
    "missing_warn": st.sidebar.slider("Missing WARN %", 0, 50, 5) / 100,
    "missing_fail": st.sidebar.slider("Missing FAIL %", 0, 100, 20) / 100,
    "psi_warn": st.sidebar.slider("Drift PSI WARN", 0.0, 1.0, 0.10),
    "psi_fail": st.sidebar.slider("Drift PSI FAIL", 0.0, 1.0, 0.25),
    "freshness_hours": st.sidebar.number_input("Freshness limit (hours)", 1, 720, 24),
}
if df is not None:
    ts_opts = ["(none)"] + list(df.columns)
    ts = st.sidebar.selectbox("Timestamp column", ts_opts)
    cfg["timestamp_column"] = None if ts == "(none)" else ts

tab_run, tab_hist, tab_help = st.tabs(["🔍 Monitor", "📈 History", "ℹ️ Help"])

# ---------- Monitor tab ----------
with tab_run:
    if df is None:
        st.info("Choose a data source in the sidebar.")
    else:
        c1, c2, c3 = st.columns([1, 1, 2])
        if c1.button("Set as baseline"):
            storage.save_baseline(checks.build_baseline(df))
            st.success("Baseline saved (schema + distributions).")
        run = c2.button("▶ Run monitoring", type="primary")
        auto = c3.checkbox("Auto re-run every 30 s (folder/path sources)")
        if run or auto:
            res = checks.run_all_checks(df, storage.load_baseline(), cfg)
            score = checks.quality_score(res)
            storage.save_run(name, df, res, score)
            alerted = alerts.send_alerts(name, res, score)
            r = pd.DataFrame(res)
            m = st.columns(4)
            m[0].metric("Quality score", f"{score}/100")
            m[1].metric("Rows", f"{len(df):,}")
            m[2].metric("FAIL", int((r.status == "FAIL").sum()))
            m[3].metric("WARN", int((r.status == "WARN").sum()))
            if alerted:
                st.warning("Alert logged to data/alerts.log (email sent if SMTP configured).")
            flt = st.multiselect("Show status", ["FAIL", "WARN", "PASS"], ["FAIL", "WARN"])
            st.dataframe(r[r.status.isin(flt)], use_container_width=True, hide_index=True)
            st.subheader("Missing values by column")
            st.bar_chart(df.isna().mean())
            with st.expander("Data preview"):
                st.dataframe(df.head(100))
            st.download_button("Download report (CSV)", r.to_csv(index=False),
                               "monitor_report.csv")
            if auto:
                time.sleep(30)
                st.rerun()

# ---------- History tab ----------
with tab_hist:
    runs = storage.load_runs()
    if runs.empty:
        st.info("No runs yet.")
    else:
        st.line_chart(runs.sort_values("id").set_index("ts")["score"])
        st.dataframe(runs, use_container_width=True, hide_index=True)
        rid = st.selectbox("Inspect run", runs["id"])
        st.dataframe(storage.load_issues(rid), use_container_width=True, hide_index=True)

with tab_help:
    st.markdown("""
**Checks:** missing values, duplicate rows, IQR outliers, schema change,
distribution drift (PSI), data freshness.
**Workflow:** load clean data → *Set as baseline* → load new data → *Run monitoring*.
**Scheduling:** `python monitor_cli.py path/to/file.csv order_date` via cron / Task Scheduler.
""")
