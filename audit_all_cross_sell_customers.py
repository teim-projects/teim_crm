import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from crmapp.models import customer_details
from crmapp.views import SEVA_PRODUCT_RELATIONSHIPS
from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine

engine = ProductRecommendationEngine(
    source_crm="seva",
    product_relationships=SEVA_PRODUCT_RELATIONSHIPS,
)

customers = customer_details.objects.only(
    "id", "fullname", "customerid"
).order_by("id")

total = 0
with_cross_sell = 0
without_cross_sell = 0
errors = 0

print("\n=== SEVA CROSS-SELL CUSTOMER AUDIT ===\n")

for customer in customers.iterator():
    total += 1
    try:
        recommendations = engine.recommend(customer.id) or []
        types = [
            str(r.get("recommendation_type") or r.get("candidate_type") or r.get("type") or "").upper()
            for r in recommendations
        ]
        cross_sells = sum(t in ("CROSS_SELL", "CROSS_SELLING") for t in types)

        if cross_sells:
            with_cross_sell += 1
            print(f"[HAS CROSS-SELL] {customer.customerid} | {customer.fullname} | {cross_sells} recommendation(s)")
        else:
            without_cross_sell += 1
            print(f"[NO CROSS-SELL]  {customer.customerid} | {customer.fullname} | Total recommendations: {len(recommendations)}")

    except Exception as exc:
        errors += 1
        print(f"[ERROR] {customer.customerid} | {customer.fullname} | {type(exc).__name__}: {exc}")

print("\n=== SUMMARY ===")
print("Customers checked:", total)
print("Customers with cross-sells:", with_cross_sell)
print("Customers without cross-sells:", without_cross_sell)
print("Customers with errors:", errors)
