from pathlib import Path
import os
import re
import pandas as pd

from src.database.crm_reader import load_live_crm_data

BASE_DIR = Path(__file__).resolve().parents[2]
XGB_FILE = BASE_DIR / "reports" / "prediction_service_live" / "xgboost_test_recommendations.csv"
OUTPUT_DIR = BASE_DIR / "reports" / "upsell_crosssell"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "xgboost_classified_recommendations.csv"
SUMMARY_FILE = OUTPUT_DIR / "xgboost_classification_summary.csv"

FAMILY_KEYWORDS = {
    "COCKROACH": ["cockroach", "roach"],
    "RODENT": ["rodent", "rat", "ratoo", "mouse", "mice"],
    "MOSQUITO": ["mosquito"],
    "BEDBUG": ["bedbug", "bed bug"],
    "TERMITE": ["termite", "anti termite"],
    "FLY": ["fly catcher", "flycatcher", "fly management", "fly control"],
    "SNAKE": ["snake"],
    "BIRD": ["bird", "pigeon"],
    "ANT": ["ant control", "ant management"],
    "DISINFECTION": ["disinfection", "sanitization", "sanitisation"],
    "WATER_PURIFIER": ["water purifier", "ro purifier", "ro system"],
    "SCALE": ["weighing scale", "bench scale", "platform scale"],
}

def normalize_id(value):
    if pd.isna(value):
        return ""
    try:
        return str(int(float(value)))
    except (ValueError, TypeError, OverflowError):
        return str(value).strip()

def clean_text(value):
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value).lower()).strip()

def normalize_category(value):
    return clean_text(value)

def identify_family(product_name):
    name = clean_text(product_name)
    matches = []

    for family, keywords in FAMILY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in name:
                matches.append((len(keyword), family))

    if matches:
        return sorted(matches, reverse=True)[0][1]

    return ""

def classify_recommendations(input_file=None, output_file=None, summary_file=None):
    input_file = Path(input_file) if input_file else XGB_FILE
    if not input_file.is_absolute():
        input_file = BASE_DIR / input_file

    output_file = Path(output_file) if output_file else OUTPUT_FILE
    summary_file = Path(summary_file) if summary_file else SUMMARY_FILE

    if not output_file.is_absolute():
        output_file = BASE_DIR / output_file
    if not summary_file.is_absolute():
        summary_file = BASE_DIR / summary_file

    print("\n========== XGBOOST UPSELL / CROSS-SELL CLASSIFIER ==========")

    if not input_file.exists():
        raise FileNotFoundError(
            f"Recommendation input file not found: {input_file}"
        )

    customers, products, interactions = load_live_crm_data()

    xgb = pd.read_csv(input_file)

    xgb["customer_id"] = xgb["customer_id"].map(normalize_id)
    xgb["product_id"] = xgb["product_id"].map(normalize_id)

    products["product_id"] = products["product_id"].map(normalize_id)
    interactions["customer_id"] = interactions["customer_id"].map(normalize_id)
    interactions["product_id"] = interactions["product_id"].map(normalize_id)

    products = products.drop_duplicates("product_id")

    product_name_lookup = (
        products.set_index("product_id")["product_name"].to_dict()
    )
    category_lookup = (
        products.set_index("product_id")["category"].to_dict()
    )

    family_lookup = {
        pid: identify_family(name)
        for pid, name in product_name_lookup.items()
    }

    # Build existing product history for each customer.
    history = (
        interactions.groupby("customer_id")["product_id"]
        .apply(lambda values: sorted(set(values.dropna())))
        .to_dict()
    )

    classifications = []

    for _, row in xgb.iterrows():
        customer_id = row["customer_id"]
        recommended_id = row["product_id"]

        recommended_name = row.get("product_name", "")
        if pd.isna(recommended_name) or not str(recommended_name).strip():
            recommended_name = product_name_lookup.get(recommended_id, "")

        recommended_category = row.get("category", "")
        if pd.isna(recommended_category) or not str(recommended_category).strip():
            recommended_category = category_lookup.get(recommended_id, "")

        recommended_family = identify_family(recommended_name)
        recommended_category_key = normalize_category(recommended_category)

        existing_products = history.get(customer_id, [])

        result = {
            "recommendation_type": "REVIEW",
            "existing_product_id": "",
            "existing_product_name": "",
            "existing_product_family": "",
            "existing_category": "",
            "recommended_product_family": recommended_family,
            "classification_reason": "",
        }

        if not existing_products:
            result["recommendation_type"] = "GENERIC"
            result["classification_reason"] = (
                "No existing customer product history available"
            )

        elif recommended_id in existing_products:
            result["recommendation_type"] = "ALREADY_OWNED"
            result["classification_reason"] = (
                "Recommended product already exists in customer history"
            )

        else:
            existing_records = []

            for existing_id in existing_products:
                existing_name = product_name_lookup.get(existing_id, "")
                existing_category = category_lookup.get(existing_id, "")

                existing_records.append({
                    "product_id": existing_id,
                    "product_name": existing_name,
                    "family": family_lookup.get(existing_id, ""),
                    "category": existing_category,
                    "category_key": normalize_category(existing_category),
                })

            # Priority 1: Same product family = UPSELL.
            same_family = [
                item for item in existing_records
                if recommended_family
                and item["family"] == recommended_family
            ]

            # Priority 2: Different identified product family = CROSS_SELL.
            different_family = [
                item for item in existing_records
                if recommended_family
                and item["family"]
                and item["family"] != recommended_family
            ]

            # Priority 3: Category fallback only when family is unavailable.
            same_category = [
                item for item in existing_records
                if not recommended_family
                and recommended_category_key
                and item["category_key"] == recommended_category_key
            ]

            different_category = [
                item for item in existing_records
                if not recommended_family
                and recommended_category_key
                and item["category_key"]
                and item["category_key"] != recommended_category_key
            ]

            if same_family:
                selected = same_family[0]
                result["recommendation_type"] = "UPSELL"
                result["classification_reason"] = (
                    "Same identified product family as existing customer product"
                )

            elif different_family:
                selected = different_family[0]
                result["recommendation_type"] = "CROSS_SELL"
                result["classification_reason"] = (
                    "Different identified product family from existing customer product"
                )

            elif same_category:
                selected = same_category[0]

                service_categories = {
                    "pest control",
                    "fumigation"
                }

                if recommended_category_key in service_categories:
                    result["recommendation_type"] = "CROSS_SELL"
                    result["classification_reason"] = (
                        "Different service opportunity within the same CRM category"
                    )
                else:
                    result["recommendation_type"] = "UPSELL"
                    result["classification_reason"] = (
                        "Product family unavailable; same non-service CRM category used as fallback"
                    )

            elif different_category:
                selected = different_category[0]
                result["recommendation_type"] = "CROSS_SELL"
                result["classification_reason"] = (
                    "Product family unavailable; different CRM category used as fallback"
                )

            else:
                selected = None
                result["recommendation_type"] = "REVIEW"
                result["classification_reason"] = (
                    "Product family and category could not establish a relationship"
                )

            if selected:
                result["existing_product_id"] = selected["product_id"]
                result["existing_product_name"] = selected["product_name"]
                result["existing_product_family"] = selected["family"]
                result["existing_category"] = selected["category"]

        classifications.append(result)

    classification_df = pd.DataFrame(classifications)

    output = pd.concat(
        [xgb.reset_index(drop=True), classification_df],
        axis=1
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_temp = output_file.with_name(
        output_file.stem + ".tmp" + output_file.suffix
    )
    try:
        output.to_csv(output_temp, index=False)
        os.replace(output_temp, output_file)
    finally:
        if output_temp.exists():
            output_temp.unlink()

    summary = (
        output.groupby("recommendation_type")
        .agg(
            recommendation_rows=("customer_id", "count"),
            unique_customers=("customer_id", "nunique")
        )
        .reset_index()
    )

    summary_temp = summary_file.with_name(
        summary_file.stem + ".tmp" + summary_file.suffix
    )
    try:
        summary.to_csv(summary_temp, index=False)
        os.replace(summary_temp, summary_file)
    finally:
        if summary_temp.exists():
            summary_temp.unlink()

    print("\n========== UPDATED CLASSIFICATION RESULTS ==========")
    print(summary.to_string(index=False))

    print("\nTotal recommendation rows:", len(output))
    print("Total unique customers:", output["customer_id"].nunique())

    print("\nOUTPUT FILES:")
    print(output_file)
    print(summary_file)

    print("\nOriginal XGBoost recommendations unchanged.")
    print("CRM database unchanged.")
    print("No model retraining performed.")

    return {
        "rows": len(output),
        "customers": output["customer_id"].nunique(),
        "output": str(output_file),
        "summary": str(summary_file),
    }

if __name__ == "__main__":
    print(classify_recommendations())
