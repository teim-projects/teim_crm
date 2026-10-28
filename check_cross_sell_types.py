
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from crmapp.models import ServiceProduct
from crmapp.product_intelligence.recommendations.recommendation_engine import (
    ProductRecommendationEngine,
)


def main():
    engine = ProductRecommendationEngine()

    customer_ids = sorted(
        set(
            ServiceProduct.objects.filter(
                service__customer__isnull=False
            ).values_list("service__customer_id", flat=True)
        ),
        key=str,
    )

    cross_sell_count = 0
    missing_type = 0
    missing_evidence = 0
    existing_product_warnings = 0

    for customer_id in customer_ids:
        recommendations = engine.recommend(customer_id)

        used_ids = set(
            ServiceProduct.objects.filter(
                service__customer_id=customer_id
            ).values_list("product_id", flat=True)
        )

        for item in recommendations:
            kind = (
                item.get("candidate_type")
                or item.get("recommendation_type")
            )

            if not kind:
                missing_type += 1

            if str(kind).upper() != "CROSS_SELL":
                continue

            cross_sell_count += 1

            if not item.get("source_products") or not item.get("reasons"):
                missing_evidence += 1

            if item.get("product_id") in used_ids:
                existing_product_warnings += 1
                print(
                    "WARNING: Suggested product already used",
                    customer_id,
                    item.get("product_name"),
                    item.get("product_id"),
                )

    print("\n=== VALIDATION SUMMARY ===")
    print("Cross-sell recommendations:", cross_sell_count)
    print("Recommendations missing type:", missing_type)
    print("Cross-sells missing source/reason evidence:", missing_evidence)
    print("Cross-sells matching previously used product IDs:", existing_product_warnings)


if __name__ == "__main__":
    main()
