from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

service_records = SevaServiceAdapter().get_universal_service_products()
invoice_records = SevaInvoiceAdapter().get_universal_invoice_products()
matched_invoices = [
    r for r in invoice_records
    if r.get("product_id") is not None
    and r.get("product_mapping_status") == "matched"
]
training_records = service_records + matched_invoices

print("Service records:", len(service_records))
print("Matched invoice records:", len(matched_invoices))
print("Training records:", len(training_records))

model = CrossSellMLEngine().fit(training_records, source_crm="seva")
products = SevaProductAdapter().get_universal_products()
product_map = {
    str(p.get("product_key") or f"seva:{p.get('product_id')}"): p
    for p in products
}

for customer_id in [85, 104, 100, 27, 109]:
    owned = {
        str(r.get("product_key") or f"seva:{r.get('product_id')}")
        for r in service_records + matched_invoices
        if str(r.get("customer_id")) == str(customer_id)
        and r.get("product_id") is not None
    }
    predictions = model.recommend(owned, limit=10)
    eligible = [
        (product_map.get(p["product_key"]), p)
        for p in predictions
        if p["product_key"] in product_map
        and p["product_key"] not in owned
    ]
    print(f"\nCustomer {customer_id}: owned={sorted(owned)}")
    print("Raw predictions:", len(predictions))
    for product, pred in eligible:
        print(
            product.get("product_name") if product else pred["product_key"],
            "confidence=", pred["confidence"],
            "support=", pred["support"],
            "lift=", pred["lift"],
        )
