
from pathlib import Path

from httpcore import request
import pandas as pd

from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from .decorators import role_required
from src.database.crm_reader import load_live_crm_data


RECOMMENDATION_FILE = (
    Path(settings.BASE_DIR)
    / "reports"
    / "prediction_service_live"
    / "latest_recommendations.csv"
)

CLASSIFIED_RECOMMENDATION_FILE = (
    Path(settings.BASE_DIR)
    / "reports"
    / "upsell_crosssell"
    / "latest_classified_recommendations.csv"
)


def clean_records(dataframe):
    """Convert DataFrame records into template-friendly values."""
    records = dataframe.to_dict(orient="records")

    for record in records:
        for key, value in record.items():
            if pd.isna(value):
                record[key] = None
            elif hasattr(value, "isoformat"):
                record[key] = value.isoformat()

    return records


@login_required
@role_required(['admin', 'sales', 'branch_manager'])
def product_recommendations(request):

    # Load live CRM data
    customers, products, interactions = load_live_crm_data()

    # Normalize IDs for reliable matching
    customers["customer_id"] = (
        customers["customer_id"].astype(str).str.strip()
    )

    interactions["customer_id"] = (
        interactions["customer_id"].astype(str).str.strip()
    )

    products["product_id"] = (
        products["product_id"].astype(str).str.strip()
    )

    interactions["product_id"] = (
        interactions["product_id"].astype(str).str.strip()
    )

    # Add product names to interaction history
    history = interactions.merge(
        products[["product_id", "product_name"]],
        on="product_id",
        how="left"
    )

    # Load saved recommendations
    if RECOMMENDATION_FILE.exists():
        recommendations = pd.read_csv(
            RECOMMENDATION_FILE,
            dtype={
                "customer_id": str,
                "product_id": str
            }
        )

        recommendations["customer_id"] = (
            recommendations["customer_id"].str.strip()
        )
    else:
        recommendations = pd.DataFrame()

    # Merge classification details into the existing live recommendations.
    classification_columns = [
        "recommendation_type",
        "classification_reason",
        "existing_product_id",
        "existing_product_name",
        "existing_product_family",
        "existing_category",
        "recommended_product_family",
    ]

    if not recommendations.empty and CLASSIFIED_RECOMMENDATION_FILE.exists():
        classified = pd.read_csv(
            CLASSIFIED_RECOMMENDATION_FILE,
            dtype={
                "customer_id": str,
                "product_id": str,
                "existing_product_id": str,
            },
        )

        merge_keys = ["customer_id", "rank", "product_id"]

        for column in ["customer_id", "product_id"]:
            classified[column] = classified[column].astype(str).str.strip()

        recommendations["rank"] = pd.to_numeric(
            recommendations["rank"], errors="coerce"
        )
        classified["rank"] = pd.to_numeric(
            classified["rank"], errors="coerce"
        )

        classified = classified[
            merge_keys + [
                column for column in classification_columns
                if column in classified.columns
            ]
        ].drop_duplicates(subset=merge_keys, keep="first")

        recommendations = recommendations.merge(
            classified,
            on=merge_keys,
            how="left",
        )

    # Keep the original recommendation display working if classification
    # has not yet been generated or a row has no matching classification.
    for column in classification_columns:
        if column not in recommendations.columns:
            recommendations[column] = None

    recommendations["recommendation_type"] = (
        recommendations["recommendation_type"].fillna("UNCLASSIFIED")
    )

    recommendations["classification_reason"] = (
        recommendations["classification_reason"].fillna(
            "Classification is not available for this recommendation."
        )
    )

    # Dashboard statistics
    total_customers = len(customers)

    customers_with_history = (
        history["customer_id"].nunique()
    )

    customers_with_recommendations = (
        recommendations["customer_id"].nunique()
        if not recommendations.empty else 0
    )

    # Selected customer
    selected_customer_id = (
           request.POST.get("customer_id")
           or request.GET.get("customer_id")
           or ""
    ).strip()

    mode = (
        request.POST.get("mode")
        or request.GET.get("mode")
        or "CROSS_SELL"
    ).strip().upper()

    if mode not in {"UPSELL", "CROSS_SELL"}:
        mode = "CROSS_SELL"

    valid_customer_ids = set(customers["customer_id"])

    if selected_customer_id not in valid_customer_ids:
        selected_customer_id = ""

    selected_customer = None
    customer_history = pd.DataFrame()
    customer_recommendations = pd.DataFrame()

    if selected_customer_id:

        customer_row = customers[
            customers["customer_id"] == selected_customer_id
        ]

        if not customer_row.empty:
            selected_customer = customer_row.iloc[0].to_dict()

        # Customer activity / product history
        customer_history = history[
            history["customer_id"] == selected_customer_id
        ].sort_values(
            "event_date",
            ascending=False
        )

        # Customer recommendations
        if not recommendations.empty:

            # Get all recommendations for the selected customer
            customer_recommendations = recommendations[
                recommendations["customer_id"] == selected_customer_id
            ].copy()

            # Check whether the customer has recorded interaction history
            customer_has_history = (
                interactions["customer_id"]
                .astype(str)
                .str.strip()
                .eq(selected_customer_id)
                .any()
            )

            if customer_has_history:
                # Customers with history: filter by selected mode
                customer_recommendations = customer_recommendations[
                    customer_recommendations["recommendation_type"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    == mode
                ]

            # Customers without history: show all original recommendations
            customer_recommendations = customer_recommendations.sort_values(
                "rank",
                ascending=True
            )
    context = {
        "mode": mode,
        "customers": clean_records(
            customers.sort_values("customer_name")
        ),

        "selected_customer": selected_customer,
        "selected_customer_id": selected_customer_id,

        "customer_history": clean_records(customer_history),
        "customer_recommendations": clean_records(
            customer_recommendations
        ),

        "total_customers": total_customers,

        "customers_with_purchase_history": customers_with_history,
        "customers_without_purchase_history": (
            total_customers - customers_with_history
        ),

        "customers_with_recommendations": (
            customers_with_recommendations
        ),

        "customers_without_recommendations": (
            total_customers - customers_with_recommendations
        ),

        "total_products": len(products),
        "total_interactions": len(interactions),
    }

    return render(
        request,
        "product_recommendations.html",
        context
    )
