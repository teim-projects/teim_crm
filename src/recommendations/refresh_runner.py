"""Scheduled/manual refresh entry point; does not train the model."""
from pathlib import Path
import os
import pandas as pd
from src.recommendations.recommendation_service_live import DEFAULT_OUTPUT, generate_recommendations, normalize_id


def refresh_recommendations(customer_id=None, output_path=None):
    output_path = Path(output_path) if output_path else DEFAULT_OUTPUT
    if customer_id is None:
        return generate_recommendations(output_path=output_path)

    target_id = normalize_id(customer_id)
    previous = pd.read_csv(output_path, dtype={"customer_id": str}) if output_path.exists() else pd.DataFrame()
    # Generate only this customer's new rows to preserve all other customers.
    from src.recommendations.recommendation_service_live import (
        load_model, load_real_interactions, prepare_customers, prepare_products,
        recommend_customer,
    )
    from src.database.crm_reader import load_live_crm_data
    model, config = load_model()
    customers, live_products, live_interactions = load_live_crm_data()
    customers = prepare_customers(customers); products = prepare_products(live_products)
    interactions = load_real_interactions(live_interactions)
    if target_id not in set(customers.customer_id):
        raise ValueError(f"Customer {target_id} does not exist in live CRM")
    refreshed = recommend_customer(target_id, customers, products, interactions, model, config)
    if not previous.empty:
        previous["customer_id"] = previous.customer_id.apply(normalize_id)
        previous = previous[previous.customer_id != target_id]
        final = pd.concat([previous, refreshed], ignore_index=True)
    else: final = refreshed
    if not final.empty: final = final.sort_values(["customer_id", "rank"], kind="stable")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_name(output_path.stem + ".tmp" + output_path.suffix)
    try:
        final.to_csv(temp, index=False); os.replace(temp, output_path)
    finally:
        if temp.exists(): temp.unlink()
    return {"customers_processed": 1, "recommendation_rows": len(refreshed), "total_output_rows": len(final), "model_version": config["model_version"], "output": str(output_path)}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--customer-id"); parser.add_argument("--output")
    args = parser.parse_args(); print(refresh_recommendations(args.customer_id, args.output))
