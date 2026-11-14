"""Creates data/sample_clean.csv (baseline) and data/sample_dirty.csv (with problems)."""
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
n = 1000


def make(dirty=False):
    df = pd.DataFrame({
        "order_id": np.arange(n),
        "order_date": pd.Timestamp.now() - pd.to_timedelta(rng.integers(0, 48, n), unit="h"),
        "customer_age": rng.normal(35, 8, n).round(),
        "amount": rng.normal(500, 100, n).round(2),
        "region": rng.choice(["North", "South", "East", "West"], n),
    })
    if dirty:
        df["amount"] = df["amount"] * 1.6                       # drift
        df.loc[rng.choice(n, 150, replace=False), "customer_age"] = np.nan  # missing
        df.loc[rng.choice(n, 30, replace=False), "amount"] = 99999          # outliers
        df = pd.concat([df, df.sample(60, random_state=1)])     # duplicates
        df["region"] = df["region"].astype(object)
        df["order_date"] = df["order_date"] - pd.Timedelta(hours=60)  # stale data
        df["coupon"] = "X1"                                     # new column
    return df


make().to_csv("data/sample_clean.csv", index=False)
make(True).to_csv("data/sample_dirty.csv", index=False)
print("Sample files created in data/")
