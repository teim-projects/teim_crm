from crmapp.models import ServiceProduct, TaxInvoiceItem
from crmapp.product_intelligence.recommendations.cross_sell_evaluation import evaluate_cross_sell_model

records = []
excluded = []

services = ServiceProduct.objects.select_related("service", "product")
for x in services:
    name = x.product.product_name.strip()
    records.append({
        "source_crm": "seva",
        "service_id": x.service_id,
        "customer_id": x.service.customer_id,
        "product_id": "name:" + name.casefold(),
        "product_name": name,
    })

invoices = TaxInvoiceItem.objects.select_related("tax_invoice")
for x in invoices:
    name = (x.product_name or "").strip()
    if not name or "charge" in name.casefold():
        excluded.append(name)
        continue
    records.append({
        "source_crm": "seva",
        "transaction_id": x.tax_invoice_id,
        "customer_id": x.tax_invoice.customer_id,
        "product_id": "name:" + name.casefold(),
        "product_name": name,
    })

print("SERVICE ROWS:", services.count())
print("INVOICE LINES:", invoices.count())
print("EXCLUDED CHARGES:", excluded)
print("CLEANED RECORDS:", len(records))

for mode in ("customer", "basket"):
    print(f"\n{mode.upper()}-LEVEL EVALUATION:")
    print(evaluate_cross_sell_model(
        records,
        test_size=0.20,
        random_state=42,
        k=5,
        split_by=mode,
    ))
