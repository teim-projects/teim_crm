from collections import defaultdict
from sklearn.model_selection import GroupShuffleSplit

from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine
from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.quotation import SevaQuotationAdapter
from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter

adapters = {
    "product_adapter": SevaProductAdapter(),
    "service_adapter": SevaServiceAdapter(),
    "quotation_adapter": SevaQuotationAdapter(),
    "amc_adapter": SevaAMCAdapter(),
}
engine = ProductRecommendationEngine(source_crm="seva", **adapters)
records = adapters["quotation_adapter"].get_universal_quotation_products()

print("\n=== DUPLICATE-NAME INSPECTION: CUSTOMER 102 ===")
items = engine.recommend(102)
for item in items:
    if "cockroach management" in str(item.get("product_name", "")).lower():
        print({
            "name": item.get("product_name"),
            "product_id": item.get("product_id"),
            "product_key": item.get("product_key"),
            "type": item.get("candidate_type"),
            "source": item.get("relationship_source"),
            "confidence": item.get("ml_confidence"),
        })

# Split by customer to prevent the same customer's quotations appearing
# in both training and testing.
customers = sorted({
    str(r.get("customer_id")) for r in records
    if r.get("customer_id") is not None
})
if len(customers) < 4:
    raise SystemExit("Not enough distinct customers for a reliable holdout.")

splitter = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
train_idx, test_idx = next(
    splitter.split(customers, groups=customers)
)
train_customers = {customers[i] for i in train_idx}
test_customers = {customers[i] for i in test_idx}

train_records = [r for r in records if str(r.get("customer_id")) in train_customers]
test_records = [r for r in records if str(r.get("customer_id")) in test_customers]

model = CrossSellMLEngine(
    min_support=0.05,
    min_confidence=0.20,
    min_lift=1.0,
)
model.fit(train_records, source_crm="seva")

baskets = defaultdict(set)
for r in test_records:
    key = r.get("product_key")
    if key:
        baskets[(str(r.get("customer_id")), str(r.get("quotation_id")))].add(key)

cases = 0
hits = 0
returned = 0
basket_count = 0

for basket in baskets.values():
    if len(basket) < 2:
        continue
    basket_count += 1
    for target in basket:
        antecedents = basket - {target}
        predictions = model.recommend(antecedents, limit=5)
        recommended_keys = [p.get("product_key") for p in predictions]
        cases += 1
        returned += len(recommended_keys)
        if target in recommended_keys:
            hits += 1

print("\n=== HELD-OUT QUOTATION EVALUATION ===")
print("Train customers:", len(train_customers))
print("Test customers:", len(test_customers))
print("Training quotation rows:", len(train_records))
print("Test quotation rows:", len(test_records))
print("Test baskets with 2+ products:", basket_count)
print("Evaluated hidden-product cases:", cases)
print("Learned rules:", len(getattr(model, "rules_", [])))
if cases:
    print(f"Hit rate@5 / recall@5: {hits / cases:.3f}")
    print(f"Precision@5 (returned-item basis): {hits / returned:.3f}" if returned else "Precision@5: no recommendations returned")
else:
    print("Metrics unavailable: no eligible held-out baskets.")
