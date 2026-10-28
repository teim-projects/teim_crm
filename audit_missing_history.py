import json
from collections import Counter
from crmapp.models import (
    customer_details, service_management, ServiceProduct,
    quotation_management, TaxInvoice, TaxInvoiceItem
)

service_product_counts = Counter(
    ServiceProduct.objects.values_list("service_id", flat=True)
)
customers_with_services = set(
    service_management.objects.values_list("customer_id", flat=True)
)
customers_with_service_products = set(
    service_management.objects.filter(
        serviceproduct__isnull=False
    ).values_list("customer_id", flat=True).distinct()
) if hasattr(service_management, "serviceproduct") else set(
    ServiceProduct.objects.values_list("service__customer_id", flat=True)
)

print("===== SERVICE HISTORY =====")
print("Service records:", service_management.objects.count())
print("Service-product rows:", ServiceProduct.objects.count())
print("Services with product rows:", len(service_product_counts))
print("Services without product rows:",
      service_management.objects.exclude(
          id__in=service_product_counts.keys()
      ).count())
print("Customers with service records:", len(customers_with_services))
print("Customers with service-product rows:", len(customers_with_service_products))

print("\n===== SERVICES WITHOUT PRODUCT ROWS =====")
for service in service_management.objects.exclude(
    id__in=service_product_counts.keys()
).select_related("customer").only(
    "id", "customer_id", "customer__fullname",
    "service_subject", "service_date", "contract_status"
)[:40]:
    print({
        "service_id": service.id,
        "customer_id": service.customer_id,
        "customer": service.customer.fullname if service.customer else None,
        "subject": service.service_subject,
        "date": str(service.service_date),
        "contract_status": service.contract_status,
    })

print("\n===== QUOTATION PRODUCT DETAILS =====")
for q in quotation_management.objects.only(
    "id", "customer_id", "quotation_no", "product_details_json",
    "quotation_date", "is_latest"
)[:15]:
    raw = q.product_details_json
    try:
        parsed = json.loads(raw) if isinstance(raw, str) and raw else raw
    except Exception:
        parsed = str(raw)[:200]
    print({
        "quotation_id": q.id,
        "customer_id": q.customer_id,
        "quotation_no": q.quotation_no,
        "is_latest": q.is_latest,
        "product_details": str(parsed)[:350],
    })

print("\n===== INVOICE ITEM MAPPING =====")
for item in TaxInvoiceItem.objects.select_related(
    "tax_invoice", "tax_invoice__customer"
).only(
    "id", "tax_invoice_id", "tax_invoice__customer_id",
    "product_name", "quantity", "description"
)[:20]:
    print({
        "item_id": item.id,
        "invoice_id": item.tax_invoice_id,
        "customer_id": item.tax_invoice.customer_id,
        "product_name": item.product_name,
        "quantity": item.quantity,
        "description": item.description,
    })
