"""Live inference service for the saved supervised XGBoost recommender."""
import argparse
import json
import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from src.database.crm_reader import load_live_crm_data
from src.recommendations.xgboost_recommender import build_history_features, make_pair_features

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_DIR = BASE_DIR / "models" / "xgboost_supervised"
DEFAULT_OUTPUT = BASE_DIR / "reports" / "prediction_service_live" / "latest_recommendations.csv"


def normalize_id(value):
    if pd.isna(value): return None
    return str(value).strip()


def load_model():
    model_path = MODEL_DIR / "xgboost_recommender.joblib"
    config_path = MODEL_DIR / "model_config.json"
    if not model_path.exists() or not config_path.exists():
        raise FileNotFoundError(
            f"Supervised model not found in {MODEL_DIR}. Run train_xgboost_model.py first."
        )
    model = joblib.load(model_path)
    with open(config_path, "r", encoding="utf-8") as f: config = json.load(f)
    return model, config


def load_real_interactions(source):
    required = ["customer_id", "product_id", "category", "confidence_weight", "data_source"]
    if not isinstance(source, pd.DataFrame): source = pd.read_csv(source)
    missing = [c for c in required if c not in source]
    if missing: raise ValueError(f"Missing live interaction columns: {missing}")
    x = source[source.data_source.eq("real_crm")].copy()
    x["customer_id"] = x.customer_id.apply(normalize_id)
    x["product_id"] = pd.to_numeric(x.product_id, errors="coerce")
    x["confidence_weight"] = pd.to_numeric(x.confidence_weight, errors="coerce").fillna(1.0)
    x = x.dropna(subset=["customer_id", "product_id", "category"]).copy()
    x["product_id"] = x.product_id.astype(int)
    if "event_date" in x: x["event_date"] = pd.to_datetime(x.event_date, errors="coerce")
    return x


def prepare_customers(customers):
    x = customers.copy()
    if "customer_id" not in x: raise ValueError("Live customers must contain customer_id")
    x["customer_id"] = x.customer_id.apply(normalize_id)
    if "branch_id" not in x: x["branch_id"] = "Unknown"
    for col in ["customer_type", "city", "state", "branch_id"]:
        if col not in x: x[col] = "Unknown"
    return x.dropna(subset=["customer_id"]).drop_duplicates("customer_id")


def prepare_products(products):
    x = products.copy()
    required = ["product_id", "product_name", "category"]
    missing = [c for c in required if c not in x]
    if missing: raise ValueError(f"Missing live product columns: {missing}")
    x["product_id"] = pd.to_numeric(x.product_id, errors="coerce")
    x = x.dropna(subset=["product_id"]).copy()
    x["product_id"] = x.product_id.astype(int)
    for col in ["hsn_code", "standard_unit", "source_category"]:
        if col not in x: x[col] = "Unknown"
    return x.drop_duplicates("product_id")


def recommend_customer(
    customer_id,
    customers,
    products,
    interactions,
    model,
    config,
    history,
    top_n=None
):
    cid = normalize_id(customer_id)

    customer_row = customers[customers.customer_id.eq(cid)]

    if customer_row.empty:
        return pd.DataFrame()

    # Use precomputed interaction history
    seen = history[3].get(cid, set())

    # Exclude products already interacted with
    candidates = products[
        ~products.product_id.isin(seen)
    ].copy()

    if candidates.empty:
        return pd.DataFrame()

    # Generate customer-product features
    features = make_pair_features(
        [cid] * len(candidates),
        candidates.product_id.tolist(),
        customers,
        products,
        history,
    )

    # XGBoost prediction
    candidates["recommendation_score"] = model.predict_proba(
        features
    )[:, 1]

    candidates = candidates.sort_values(
        ["recommendation_score", "product_id"],
        ascending=[False, True]
    )

    limit = int(top_n or config.get("top_n", 10))

    result = candidates.head(limit).copy()

    result.insert(0, "customer_id", cid)
    result.insert(1, "rank", range(1, len(result) + 1))

    result["combined_similarity"] = 0.0
    result["combined_popularity"] = 0.0
    result["category_preference"] = 0.0

    result["recommendation_evidence"] = (
        "Supervised-model prediction"
        if cid in history[3]
        else "Cold-start profile prediction"
    )

    result["recommendation_source"] = "XGBoost supervised model"
    result["model_version"] = config["model_version"]
    result["is_actual_purchase"] = False

    return result[
        [
            "customer_id",
            "rank",
            "product_id",
            "product_name",
            "category",
            "recommendation_score",
            "combined_similarity",
            "combined_popularity",
            "category_preference",
            "recommendation_evidence",
            "recommendation_source",
            "model_version",
            "is_actual_purchase",
        ]
    ]


def generate_recommendations(customer_id=None, output_path=None):
    model, config = load_model()
    customers, live_products, live_interactions = load_live_crm_data()
    customers = prepare_customers(customers)
    products = prepare_products(live_products)
    interactions = load_real_interactions(live_interactions)
    # Build customer-product interaction history only once
    print("Building customer interaction history...")

    history = build_history_features(interactions)

    print("Interaction history built successfully.")
    if customer_id is None: ids = customers.customer_id.tolist()
    else:
        target = normalize_id(customer_id)
        if target not in set(customers.customer_id): raise ValueError(f"Customer {target} does not exist in live CRM")
        ids = [target]
    results = []
    for cid in ids:
        result = recommend_customer(cid, customers, products, interactions, model, config, history)
        if not result.empty: results.append(result)
        print(f"Customer {cid}: {len(result)} recommendations")
    columns = ["customer_id", "rank", "product_id", "product_name", "category", "recommendation_score", "combined_similarity", "combined_popularity", "category_preference", "recommendation_evidence", "recommendation_source", "model_version", "is_actual_purchase"]
    refreshed = pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=columns)
    path = Path(output_path) if output_path else DEFAULT_OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.stem + ".tmp" + path.suffix)
    try:
        refreshed.to_csv(temp_path, index=False)
        os.replace(temp_path, path)
    finally:
        if temp_path.exists(): temp_path.unlink()
    print("Model:", config["model_version"])
    print("Customers processed:", len(ids), "| Recommendation rows:", len(refreshed))
    print("Live products considered:", len(products), "| Model retrained: No")
    print("Output:", path)
    return {"customers_processed": len(ids), "recommendation_rows": len(refreshed), "model_version": config["model_version"], "output": str(path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--customer-id")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    generate_recommendations(args.customer_id, args.output)

if __name__ == "__main__": main()
