import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teim_crm.settings")
import django
django.setup()
from django.test import Client
from crmapp.models import customer_details, ServiceProduct, TaxInvoiceItem

client = Client(HTTP_HOST="localhost")
generated = []
empty = []
errors = []

for c in customer_details.objects.only("id", "fullname").iterator():
    has_history = (
        ServiceProduct.objects.filter(service__customer_id=c.id).exists()
        or TaxInvoiceItem.objects.filter(tax_invoice__customer_id=c.id).exists()
    )
    if not has_history:
        continue

    r = client.post("/product-recommendations/", {
        "customer_id": str(c.id),
        "mode": "CROSS_SELL",
    })
    html = r.content.decode("utf-8", errors="replace")

    if r.status_code != 200:
        errors.append((c.id, f"HTTP {r.status_code}"))
    elif "Could not generate recommendations:" in html:
        errors.append((c.id, "Recommendation error"))
    elif "Purchase history found, but no eligible cross-sell recommendations" in html:
        empty.append(c.id)
    else:
        generated.append(c.id)

print("Customers with recommendations/results:", len(generated))
print("Customer IDs:", generated)
print("Customers with no eligible recommendations:", len(empty))
print("No-recommendation IDs:", empty)
print("Errors:", errors)
