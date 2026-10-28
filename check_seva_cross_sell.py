from collections import Counter
from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.quotation import SevaQuotationAdapter
from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter

engine = ProductRecommendationEngine(
    source_crm="seva",
    product_adapter=SevaProductAdapter(),
    service_adapter=SevaServiceAdapter(),
    quotation_adapter=SevaQuotationAdapter(),
    amc_adapter=SevaAMCAdapter(),
)

services = engine.service_adapter.get_universal_service_products()
quotes = engine.quotation_adapter.get_universal_quotation_products()
customer_ids = sorted({
    r["customer_id"] for r in services + quotes
    if r.get("customer_id") is not None
}, key=str)

print("Service rows:", len(services))
print("Quotation rows:", len(quotes))
print("Customers:", len(customer_ids))

counts = Counter()
samples = []

for customer_id in customer_ids:
    try:
        result = engine.recommend(customer_id)
        items = result.get("recommendations", result.get("results", [])) if isinstance(result, dict) else result
        if not isinstance(items, (list, tuple)):
            print("Unexpected result:", customer_id, repr(items)[:200])
            continue

        counts["customers_tested"] += 1
        counts["total_recommendations"] += len(items)

        for item in items:
            counts[item.get("relationship_source") or "NO_ML_SOURCE"] += 1
            if item.get("candidate_type") == "CROSS_SELL":
                counts["cross_sell"] += 1
            if len(samples) < 10:
                samples.append((
                    customer_id,
                    item.get("product_name"),
                    item.get("candidate_type"),
                    item.get("relationship_source"),
                    item.get("ml_confidence"),
                    item.get("ml_lift"),
                ))
    except Exception as exc:
        counts["customer_errors"] += 1
        print("ERROR customer", customer_id, type(exc).__name__, str(exc)[:250])

print("\n=== COUNTS ===")
for key, value in counts.items():
    print(f"{key}: {value}")

print("\n=== SAMPLE RECOMMENDATIONS ===")
for sample in samples:
    print(sample)

print("\n=== QUOTATION MODEL ===")
model = engine.quotation_cross_sell_ml_engine
for attr in ("rules", "association_rules", "rules_"):
    if hasattr(model, attr):
        try:
            print(attr, len(getattr(model, attr)))
        except TypeError:
            print(attr, type(getattr(model, attr)).__name__)
        break
