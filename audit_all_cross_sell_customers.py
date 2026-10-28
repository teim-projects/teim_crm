from collections import Counter
from django.test import Client
from django.test.utils import setup_test_environment
from crmapp.models import customer_details

setup_test_environment()
client = Client()
customers = customer_details.objects.all().only("id").order_by("id")

total = 0
with_recommendations = 0
without_recommendations = 0
errors = Counter()
examples_without = []

for customer in customers.iterator():
    total += 1
    response = client.post(
        "/product-recommendations/",
        {"customer_id": str(customer.id), "mode": "CROSS_SELL"},
        HTTP_HOST="localhost",
    )

    if response.status_code != 200 or response.context is None:
        errors[f"HTTP/context issue: {response.status_code}"] += 1
        continue

    ctx = response.context
    recs = ctx.get("recommendations", [])
    if recs:
        with_recommendations += 1
    else:
        without_recommendations += 1
        if len(examples_without) < 15:
            examples_without.append((
                customer.id,
                ctx.get("cross_sell_status"),
                ctx.get("error_message"),
            ))

print("\n===== ALL-CUSTOMER CROSS-SELL AUDIT =====")
print("Customers checked:", total)
print("With recommendations:", with_recommendations)
print("Without recommendations:", without_recommendations)
print("Errors:", dict(errors))
print("\nSample customers without recommendations:")
for item in examples_without:
    print(item)
