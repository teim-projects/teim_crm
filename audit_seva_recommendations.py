
import os
import django
from collections import Counter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from crmapp.models import Product, ServiceProduct, quotation_management

from crmapp.product_intelligence.recommendations.recommendation_engine import (
    ProductRecommendationEngine,
)
from crmapp.product_intelligence.crm_adapters.seva.product import (
    SevaProductAdapter,
)
from crmapp.product_intelligence.crm_adapters.seva.service import (
    SevaServiceAdapter,
)
from crmapp.product_intelligence.crm_adapters.seva.quotation import (
    SevaQuotationAdapter,
)
from crmapp.product_intelligence.crm_adapters.seva.amc import (
    SevaAMCAdapter,
)
from crmapp.product_intelligence.crm_adapters.seva.recommendation_config import (
    SEVA_PRODUCT_RELATIONSHIPS,
)
from crmapp.product_intelligence.recommendations.upsell_rules import (
    SevaUpsellRules,
)


def get_recommendations(result):
    """Normalize supported recommendation response formats."""
    if isinstance(result, dict):
        recommendations = result.get("recommendations", [])
    elif isinstance(result, list):
        recommendations = result
    else:
        recommendations = []

    return [
        item for item in recommendations
        if isinstance(item, dict)
    ]


def get_recommendation_type(item):
    """Read the recommendation type across supported output formats."""
    value = (
        item.get("recommendation_type")
        or item.get("candidate_type")
        or item.get("type")
        or ""
    )
    return str(value).upper().replace("-", "_").replace(" ", "_")


def main():
    print("=" * 70)
    print("SEVA PRODUCT INTELLIGENCE AUDIT")
    print("=" * 70)

    # Use the same CRM-specific dependencies as the application.
    engine = ProductRecommendationEngine(
        source_crm="seva",
        product_adapter=SevaProductAdapter(),
        service_adapter=SevaServiceAdapter(),
        quotation_adapter=SevaQuotationAdapter(),
        amc_adapter=SevaAMCAdapter(),
        product_relationships=SEVA_PRODUCT_RELATIONSHIPS,
        allow_historical_cross_sell=True,
        upsell_rule_provider=SevaUpsellRules(),
    )

    # 1. Source data
    print("\n1. SOURCE DATA")
    print(f"Products in catalogue: {Product.objects.count()}")
    print(f"Service-product records: {ServiceProduct.objects.count()}")
    print(f"Quotations: {quotation_management.objects.count()}")

    service_rows = list(
        ServiceProduct.objects.values(
            "service__customer_id",
            "service_id",
            "product_id",
            "product__product_name",
        )
    )

    customer_ids = sorted(
        {
            row["service__customer_id"]
            for row in service_rows
            if row["service__customer_id"] is not None
        },
        key=str,
    )

    print(f"Service-product rows loaded: {len(service_rows)}")
    print(
        "Rows with customer IDs:",
        sum(
            1 for row in service_rows
            if row["service__customer_id"] is not None
        ),
    )
    print(f"Distinct customers with service products: {len(customer_ids)}")

    print("\nConfigured complementary relationships:")
    for relationship in SEVA_PRODUCT_RELATIONSHIPS:
        print(
            f"  {relationship.get('source_product_key')} -> "
            f"{relationship.get('target_product_key')} "
            f"(strength={relationship.get('strength')})"
        )

    upsell_rules = SevaUpsellRules()
    configured_upsell_count = sum(
        len(upsell_rules.get_upsell_products(source_key))
        for source_key in getattr(upsell_rules, "rules", {})
    )
    print(f"Configured upsell rules: {configured_upsell_count}")

    # 2. Audit recommendations for every customer with service history.
    print("\n2. RECOMMENDATION RESULTS")

    totals = Counter()
    customers_with_cross_sell = 0
    customers_with_upsell = 0
    errors = []

    for customer_id in customer_ids:
        try:
            result = engine.recommend(customer_id)
            recommendations = get_recommendations(result)

            cross_sells = [
                item for item in recommendations
                if get_recommendation_type(item)
                in {"CROSS_SELL", "CROSS_SELLING"}
            ]
            upsells = [
                item for item in recommendations
                if get_recommendation_type(item)
                in {"UPSELL", "UPSELLING"}
            ]

            totals["customers_checked"] += 1
            totals["recommendations"] += len(recommendations)
            totals["cross_sells"] += len(cross_sells)
            totals["upsells"] += len(upsells)

            if cross_sells:
                customers_with_cross_sell += 1
                print(
                    f"\nCustomer {customer_id}: "
                    f"{len(cross_sells)} cross-sell(s)"
                )

                for item in cross_sells[:5]:
                    print(
                        "  -",
                        item.get("product_name", item.get("product_key")),
                        "| Score:",
                        item.get("score"),
                        "| Source:",
                        item.get("relationship_source"),
                        "| Reason:",
                        item.get("relationship_reason")
                        or item.get("reasons"),
                    )

            if upsells:
                customers_with_upsell += 1
                print(
                    f"\nCustomer {customer_id}: "
                    f"{len(upsells)} upsell(s)"
                )

                for item in upsells[:5]:
                    print(
                        "  -",
                        item.get("product_name", item.get("product_key")),
                        "| Score:",
                        item.get("score"),
                        "| Upgrade from:",
                        item.get("upgrade_source_product_key"),
                        "| Reason:",
                        item.get("upgrade_reason")
                        or item.get("relationship_reason"),
                    )

            if not recommendations:
                totals["customers_without_recommendations"] += 1

        except Exception as exc:
            errors.append((customer_id, repr(exc)))

    # 3. Summary
    print("\n" + "=" * 70)
    print("3. AUDIT SUMMARY")
    print("=" * 70)
    print(f"Customers with service history: {len(customer_ids)}")
    print(f"Customers checked successfully: {totals['customers_checked']}")
    print(
        "Customers without recommendations:",
        totals["customers_without_recommendations"],
    )
    print(f"Customers with cross-sells: {customers_with_cross_sell}")
    print(f"Customers with upsells: {customers_with_upsell}")
    print(f"Total recommendations: {totals['recommendations']}")
    print(f"Total cross-sell recommendations: {totals['cross_sells']}")
    print(f"Total upsell recommendations: {totals['upsells']}")
    print(f"Customer errors: {len(errors)}")

    if errors:
        print("\nFirst 10 errors:")
        for customer_id, error in errors[:10]:
            print(f"  ERROR customer {customer_id}: {error}")

    print("\nAudit completed.")


if __name__ == "__main__":
    main()
