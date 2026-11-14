import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pandas as pd, numpy as np
from monitor import checks


def test_detects_missing_and_dupes():
    df = pd.DataFrame({"a": [1, None, None, None, 5, 6, 7, 8, 9, 10] * 2})
    df = pd.concat([df, df.head(5)])
    res = checks.run_all_checks(df)
    assert any(r["check"] == "missing_values" and r["status"] == "FAIL" for r in res)
    assert any(r["check"] == "duplicate_rows" and r["status"] != "PASS" for r in res)


def test_drift_and_schema():
    rng = np.random.default_rng(0)
    base = pd.DataFrame({"x": rng.normal(0, 1, 500)})
    b = checks.build_baseline(base)
    cur = pd.DataFrame({"x": rng.normal(3, 1, 500), "new": 1})
    res = checks.run_all_checks(cur, b)
    assert any(r["check"] == "drift_psi" and r["status"] == "FAIL" for r in res)
    assert any(r["check"] == "schema" and r["detail"] == "new column" for r in res)
