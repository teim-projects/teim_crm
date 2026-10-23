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

segments = Counter()
types_by_segment = {}
examples = {}

customers = customer_details.objects.only(
    "id", "fullname", "customerid"
).order_by("id")

for customer in customers.iterator():
    has_service = customer.id in service_customers
    has_quote = customer.id in quotation_customers

    if has_service and has_quote:
        segment = "BOTH SERVICE + QUOTATION"
    elif has_service:
        segment = "SERVICE ONLY"
    elif has_quote:
        segment = "QUOTATION ONLY"
    else:
        segment = "NEITHER SERVICE NOR QUOTATION"

    recommendations = engine.recommend(customer.id) or []
    rec_types = Counter(
        str(
            item.get("recommendation_type")
            or item.get("candidate_type")
            or item.get("type")
            or "UNKNOWN"
        ).upper()
        for item in recommendations
    )

    segments[segment] += 1
    types_by_segment.setdefault(segment, Counter()).update(rec_types)

    if segment not in examples:
        examples[segment] = (
            customer.customerid,
            customer.fullname,
            len(recommendations),
            dict(rec_types),
        )

print("\n=== CUSTOMER SEGMENT AUDIT ===")
for segment, count in segments.items():
    print(f"\n{segment}: {count} customers")
    print("Recommendation types:", dict(types_by_segment[segment]))
    print("Example:", examples[segment])

print("\nTotal customers checked:", sum(segments.values()))
