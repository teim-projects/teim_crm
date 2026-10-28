import os
import django
from collections import Counter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db import connection
from crmapp.models import customer_details
from crmapp.views import SEVA_PRODUCT_RELATIONSHIPS
from crmapp.product_intelligence.recommendations.recommendation_engine import (
    ProductRecommendationEngine,
)

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT DISTINCT customer_id
        FROM crmapp_quotation_management
        WHERE customer_id IS NOT NULL
    """)
    quotation_customer_ids = {row[0] for row in cursor.fetchall()}

engine = ProductRecommendationEngine(
    source_crm="seva",
    product_relationships=SEVA_PRODUCT_RELATIONSHIPS,
)

type_counts = Counter()
customers_with_recommendations = 0
customers_with_quotation_recommendations = 0
customers_without_recommendations = []
customers_without_quote_type = []

customers = customer_details.objects.only(
    "id", "fullname", "customerid"
).filter(id__in=quotation_customer_ids).order_by("id")

print("\n=== QUOTATION RECOMMENDATION AUDIT ===")

for customer in customers:
    recommendations = engine.recommend(customer.id) or []

    types = [
        str(
            item.get("recommendation_type")
            or item.get("candidate_type")
            or item.get("type")
            or "UNKNOWN"
        ).upper()
        for item in recommendations
    ]

    type_counts.update(types)

    if recommendations:
        customers_with_recommendations += 1
    else:
        customers_without_recommendations.append(customer.customerid)

    if any("QUOTATION" in value for value in types):
        customers_with_quotation_recommendations += 1
    else:
        customers_without_quote_type.append(customer.customerid)

    print(
        f"{customer.customerid} | {customer.fullname} | "
        f"Total recommendations: {len(recommendations)} | "
        f"Types: {dict(Counter(types))}"
    )

print("\n=== SUMMARY ===")
print("Quotation customers checked:", len(quotation_customer_ids))
print("Customers with any recommendations:", customers_with_recommendations)
print(
    "Customers with QUOTATION-type recommendations:",
    customers_with_quotation_recommendations,
)
print("Recommendation counts by type:", dict(type_counts))
print("Customers with no recommendations:", customers_without_recommendations)
print("Customers without QUOTATION-type recommendations:", customers_without_quote_type)
