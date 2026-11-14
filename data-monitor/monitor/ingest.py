"""MEMBER 1 - Ingestion: CSV / Excel / JSON files."""
import pandas as pd


def load_file(path_or_buffer, name="data.csv"):
    n = name.lower()
    if n.endswith(".csv"):
        return pd.read_csv(path_or_buffer)
    if n.endswith((".xlsx", ".xls")):
        return pd.read_excel(path_or_buffer)
    if n.endswith(".json"):
        return pd.read_json(path_or_buffer)
    raise ValueError("Supported formats: csv, xlsx, json")
