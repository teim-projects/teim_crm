from collections import defaultdict
from crmapp.models import ServiceProduct
from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine

records = [
    {
        "source_crm": "seva",
        "customer_id": row.service.customer_id,
        "service_id": row.service_id,
        "product_id": row.product_id,
    }
    for row in ServiceProduct.objects.select_related("service", "product").all()
]

model = CrossSellMLEngine().fit(records)
customer_products = defaultdict(set)

for row in records:
    if row["customer_id"] is not None:
        customer_products[row["customer_id"]].add(model._product_key(row))

print("CUSTOMERS CHECKED:", len(customer_products))
print("ML RULES:", len(model.rules_))

found = 0
for customer_id, purchased in customer_products.items():
    suggestions = model.recommend(sorted(purchased), limit=20)
    unseen = [item for item in suggestions if item["product_key"] not in purchased]
    if unseen:
        found += 1
        print("\nCUSTOMER:", customer_id)
        print("PURCHASED:", sorted(purchased))
        print("UNSEEN ML RECOMMENDATIONS:", unseen)

print("\nCUSTOMERS WITH GENUINELY NEW ML RECOMMENDATIONS:", found)