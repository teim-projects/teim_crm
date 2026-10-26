import os
import django

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
        FROM crmapp_service_management
        WHERE customer_id IS NOT NULL
    """)
    service_customers = {row[0] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT DISTINCT customer_id
        FROM crmapp_quotation_management
        WHERE customer_id IS NOT NULL
    """)
    quotation_customers = {row[0] for row in cursor.fetchall()}

engine = ProductRecommendationEngine(
    source_crm="seva",
    product_relationships=SEVA_PRODUCT_RELATIONSHIPS,
)

print("\n=== CUSTOMERS WITH HISTORY BUT ZERO RECOMMENDATIONS ===")

customers = customer_details.objects.only(
    "id", "fullname", "customerid"
).order_by("id")

found = 0

for customer in customers.iterator():
    has_service = customer.id in service_customers
    has_quote = customer.id in quotation_customers

    if not (has_service or has_quote):
        continue

    recommendations = engine.recommend(customer.id) or []

    if not recommendations:
        found += 1
        print(
            f"ID={customer.id} | "
            f"Code={customer.customerid} | "
            f"Name={customer.fullname} | "
            f"Service={has_service} | "
            f"Quotation={has_quote}"
        )

print("\nTotal customers with history but zero recommendations:", found)
