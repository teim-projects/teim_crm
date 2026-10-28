from collections import Counter
from crmapp.models import customer_details
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine

customers = list(customer_details.objects.only("id", "fullname").order_by("id"))
services = SevaServiceAdapter().get_universal_service_products()
invoices = SevaInvoiceAdapter().get_universal_invoice_products()
products = SevaProductAdapter().get_universal_products()

matched_invoices = [
    r for r in invoices
    if r.get("product_id") is not None
    and r.get("product_mapping_status") == "matched"
]
model = CrossSellMLEngine().fit(
    services + matched_invoices, source_crm="seva"
)
product_map = {
    str(p.get("product_key") or f"seva:{p.get('product_id')}"): p
    for p in products
}

counts = Counter()
zero_examples = []

for customer in customers:
    cid = str(customer.id)
    history = [
        r for r in services + invoices
        if str(r.get("customer_id")) == cid
    ]
    owned = {
        str(r.get("product_key") or f"seva:{r.get('product_id')}")
        for r in history if r.get("product_id") is not None
    }
    counts["with_history" if history else "without_history"] += 1

    predictions = model.recommend(owned, limit=10)
    valid = [
        p for p in predictions
        if p.get("product_key") in product_map
        and p.get("product_key") not in owned
    ]
    counts["recommendations_total"] += len(valid)

    if valid:
        counts["customers_with_recommendations"] += 1
    else:
        counts["zero_recommendations"] += 1
        if len(zero_examples) < 15:
            zero_examples.append(
                f"{customer.id} | {customer.fullname} | "
                f"history={len(history)} | owned={len(owned)}"
            )

print("\n===== REAL SEVA CROSS-SELL COVERAGE =====")
print("Total customers:", len(customers))
print("Customers with purchase records:", counts["with_history"])
print("Customers without purchase records:", counts["without_history"])
print("Customers receiving recommendations:", counts["customers_with_recommendations"])
print("Customers receiving zero recommendations:", counts["zero_recommendations"])
print("Total valid recommendations:", counts["recommendations_total"])
print("\nFirst zero-result customers (ID | name | history | owned):")
for row in zero_examples:
    print(row)
