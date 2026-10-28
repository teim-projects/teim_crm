from django.test import Client
from django.test.utils import setup_test_environment

setup_test_environment()
client = Client()

for customer_id in [85, 104, 100, 27, 109]:
    response = client.post(
        "/product-recommendations/",
        {"customer_id": str(customer_id), "mode": "CROSS_SELL"},
        HTTP_HOST="localhost",
    )
    print(f"\nCustomer {customer_id} | HTTP {response.status_code}")
    print("Template context available:", response.context is not None)
    if response.context:
        ctx = response.context
        print("Recommendation count:", len(ctx.get("recommendations", [])))
        print("Status:", ctx.get("cross_sell_status"))
        for rec in ctx.get("recommendations", []):
            print("-", rec.get("product_name"))
    else:
        print(response.content.decode("utf-8", errors="replace")[:250])
