from collections import Counter
from crmapp.models import customer_details
from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter

services = SevaServiceAdapter().get_universal_service_products()
invoices = SevaInvoiceAdapter().get_universal_invoice_products()
matched_invoices = [
    r for r in invoices
    if r.get("product_id") is not None
    and r.get("product_mapping_status") == "matched"
]
training = services + matched_invoices
model = CrossSellMLEngine().fit(training, source_crm="seva")

products = SevaProductAdapter().get_universal_products()
product_map = {
    str(p.get("product_key") or f"seva:{p.get('product_id')}"): p
    for p in products
}

customers = list(customer_details.objects.all().only("id").order_by("id"))
counts = Counter()
no_history = []
history_no_rules = []
filtered_all = []
catalog_misses = []
examples = []

for customer in customers:
    cid = str(customer.id)
    history = [
        r for r in training
        if str(r.get("customer_id")) == cid
        and r.get("product_id") is not None
    ]
    owned = {
        str(r.get("product_key") or f"seva:{r.get('product_id')}")
        for r in history
    }
    raw = model.recommend(owned, limit=10)
    eligible = [
        p for p in raw
        if p.get("product_key") in product_map
        and p.get("product_key") not in owned
    ]

    counts["customers"] += 1
    if not history:
        counts["no_purchase_history"] += 1
        no_history.append(cid)
    else:
        counts["with_purchase_history"] += 1
        if not raw:
            counts["history_but_no_ml_match"] += 1
            history_no_rules.append(cid)
        elif not eligible:
            counts["predictions_filtered_out"] += 1
            filtered_all.append(cid)

    counts["raw_predictions"] += len(raw)
    counts["eligible_recommendations"] += len(eligible)
    counts["catalog_misses"] += sum(
        p.get("product_key") not in product_map for p in raw
    )

    if history and (not raw or not eligible) and len(examples) < 20:
        examples.append({
            "customer": cid,
            "owned": sorted(owned),
            "raw_predictions": [
                p.get("product_key") for p in raw
            ],
            "eligible": [p.get("product_key") for p in eligible],
        })

print("\n===== CUSTOMER COVERAGE ROOT-CAUSE AUDIT =====")
for key, value in counts.items():
    print(f"{key}: {value}")
print("\nNo purchase history (first 30):", no_history[:30])
print("History but no ML match (first 30):", history_no_rules[:30])
print("Predictions all filtered out (first 30):", filtered_all[:30])
print("\nExamples:")
for row in examples:
    print(row)
