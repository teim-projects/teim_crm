"""Shared feature engineering for supervised CRM product recommendations."""
from __future__ import annotations
import numpy as np
import pandas as pd

CUSTOMER_CATEGORICAL = ["customer_type", "city", "state", "branch_id"]
PRODUCT_CATEGORICAL = ["product_name", "category", "hsn_code", "standard_unit", "source_category"]
NUMERIC_FEATURES = [
    "customer_history_events", "customer_unique_products", "customer_history_weight",
    "customer_days_since_last_event", "customer_category_events", "customer_category_share",
    "product_history_events", "product_unique_customers", "product_history_weight",
    "customer_product_category_match", "customer_has_history",
]
FEATURE_COLUMNS = CUSTOMER_CATEGORICAL + PRODUCT_CATEGORICAL + NUMERIC_FEATURES


def _clean_id(series):
    return series.astype(str).str.strip()


def build_history_features(interactions: pd.DataFrame):
    x = interactions.copy()
    x["customer_id"] = _clean_id(x["customer_id"])
    x["product_id"] = pd.to_numeric(x["product_id"], errors="coerce")
    x["confidence_weight"] = pd.to_numeric(x["confidence_weight"], errors="coerce").fillna(1.0)
    x = x.dropna(subset=["customer_id", "product_id"]).copy()
    x["product_id"] = x["product_id"].astype(int)
    if "event_date" in x:
        x["event_date"] = pd.to_datetime(x["event_date"], errors="coerce")
    cust = x.groupby("customer_id").agg(
        customer_history_events=("product_id", "size"),
        customer_unique_products=("product_id", "nunique"),
        customer_history_weight=("confidence_weight", "sum"),
        _last_event=("event_date", "max") if "event_date" in x else ("product_id", "max"),
    ).reset_index()
    if "event_date" in x:
        latest = x["event_date"].max()
        cust["customer_days_since_last_event"] = (latest - cust["_last_event"]).dt.days.fillna(9999)
    else:
        cust["customer_days_since_last_event"] = 9999
    cust = cust.drop(columns=["_last_event"])
    prod = x.groupby("product_id").agg(
        product_history_events=("customer_id", "size"),
        product_unique_customers=("customer_id", "nunique"),
        product_history_weight=("confidence_weight", "sum"),
    ).reset_index()
    if "category" in x:
        cat = x.groupby(["customer_id", "category"]).size().rename("customer_category_events").reset_index()
        cat["customer_category_share"] = cat["customer_category_events"] / cat.groupby("customer_id")["customer_category_events"].transform("sum").clip(lower=1)
    else:
        cat = pd.DataFrame(columns=["customer_id", "category", "customer_category_events", "customer_category_share"])
    seen = {
       str(customer_id): set(group["product_id"].astype(int).tolist())
       for customer_id, group in x.groupby("customer_id", sort=False)
    }
    return cust, prod, cat, seen


def make_pair_features(customer_ids, product_ids, customer_table, product_table, history, customer_id_col="customer_id"):
    cust_hist, prod_hist, cat_hist, _ = history
    pairs = pd.DataFrame({"customer_id": _clean_id(pd.Series(customer_ids)), "product_id": pd.to_numeric(pd.Series(product_ids), errors="coerce")})
    pairs["product_id"] = pairs["product_id"].fillna(-1).astype(int)
    c = customer_table.copy()
    c["customer_id"] = _clean_id(c[customer_id_col])
    ccols = ["customer_id"] + [x for x in CUSTOMER_CATEGORICAL if x in c.columns]
    pairs = pairs.merge(c[ccols].drop_duplicates("customer_id"), on="customer_id", how="left")
    p = product_table.copy()
    p["product_id"] = pd.to_numeric(p["product_id"], errors="coerce")
    p = p.dropna(subset=["product_id"]).copy(); p["product_id"] = p["product_id"].astype(int)
    pcols = ["product_id"] + [x for x in PRODUCT_CATEGORICAL if x in p.columns]
    pairs = pairs.merge(p[pcols].drop_duplicates("product_id"), on="product_id", how="left")
    pairs = pairs.merge(cust_hist, on="customer_id", how="left")
    pairs = pairs.merge(prod_hist, on="product_id", how="left")
    pairs = pairs.merge(cat_hist, on=["customer_id", "category"], how="left")
    pairs["customer_product_category_match"] = pairs["customer_category_share"].fillna(0.0)
    pairs["customer_has_history"] = (pairs["customer_history_events"].fillna(0) > 0).astype(int)
    for col in FEATURE_COLUMNS:
        if col not in pairs: pairs[col] = np.nan
    for col in NUMERIC_FEATURES:
        pairs[col] = pd.to_numeric(pairs[col], errors="coerce").fillna(0.0)
    for col in CUSTOMER_CATEGORICAL + PRODUCT_CATEGORICAL:
        pairs[col] = pairs[col].fillna("Unknown").astype(str)
    return pairs[FEATURE_COLUMNS]
