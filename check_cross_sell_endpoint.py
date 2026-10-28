from django.test import Client
from django.urls import reverse

client = Client()
for customer_id in [85, 104, 100, 27, 109]:
    response = client.post(
        reverse("product_recommendations"),
        {"customer_id": str(customer_id), "mode": "CROSS_SELL"},
        HTTP_HOST="localhost",
    )
    print(f"\nCustomer {customer_id}: HTTP {response.status_code}")
    ctx = getattr(response, "context", None)
    if ctx:
        print("Count:", len(ctx.get("recommendations", [])))
        print("Status:", ctx.get("cross_sell_status"))
        for rec in ctx.get("recommendations", []):
            print(rec.get("product_name"), rec.get("ml_confidence"))
    else:
        print("No template context; inspect response content.")
        print(response.content.decode("utf-8", errors="replace")[:500])
