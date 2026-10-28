
from django.test import Client
from django.test.utils import setup_test_environment
from crmapp.models import customer_details, ServiceProduct, TaxInvoiceItem

setup_test_environment()
client = Client()

service_ids = set(
    ServiceProduct.objects.values_list("service__customer_id", flat=True)
)
invoice_ids = set(
    TaxInvoiceItem.objects.values_list("tax_invoice__customer_id", flat=True)
)
history_ids = service_ids | invoice_ids

print("\\n=== SCENARIO 2: HISTORY, ZERO ELIGIBLE CROSS-SELL ===")
customer = customer_details.objects.filter(pk=16).first()
if not customer or customer.pk not in history_ids:
    customer = customer_details.objects.filter(pk__in=history_ids).first()

if customer:
    response = client.post(
        "/product-recommendations/",
        {"customer_id": str(customer.pk), "mode": "CROSS_SELL"},
    )
    html = response.content.decode("utf-8", errors="replace")
    print("Customer ID:", customer.pk)
    print("HTTP status:", response.status_code)
    print("Redirect:", response.get("Location"))
    print("History empty-state present:",
          "Purchase records found, but no eligible ML cross-sell recommendations" in html)
    print("No-history state incorrectly shown:",
          "No recorded purchase history" in html)
else:
    print("BLOCKED: No customer with purchase history found.")

print("\\n=== SCENARIO 3: NO PURCHASE HISTORY ===")
customer = customer_details.objects.exclude(pk__in=history_ids).first()

if customer:
    response = client.post(
        "/product-recommendations/",
        {"customer_id": str(customer.pk), "mode": "CROSS_SELL"},
    )
    html = response.content.decode("utf-8", errors="replace")
    print("Customer ID:", customer.pk)
    print("HTTP status:", response.status_code)
    print("Redirect:", response.get("Location"))
    print("No-history empty-state present:",
          "No recorded purchase history" in html)
    print("Purchase-history empty-state incorrectly shown:",
          "Purchase records found, but no eligible ML cross-sell recommendations" in html)
else:
    print("BLOCKED: No customer without purchase history found.")
