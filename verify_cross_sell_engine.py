from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.quotation import SevaQuotationAdapter
from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter
from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine

service_adapter = SevaServiceAdapter()
product_adapter = SevaProductAdapter()
quotation_adapter = SevaQuotationAdapter()
amc_adapter = SevaAMCAdapter()

services = service_adapter.get_universal_service_products()
products = product_adapter.get_universal_products()
quotations = quotation_adapter.get_universal_quotation_products()
amcs = amc_adapter.get_universal_amc_products()

engine = ProductRecommendationEngine(
    source_crm="seva",
    product_adapter=product_adapter,
    service_adapter=service_adapter,
    quotation_adapter=quotation_adapter,
    amc_adapter=amc_adapter,
    product_relationships=[],
    allow_historical_cross_sell=False,
)

customer_id = 35
purchased = [
    r for r in services
    if engine.candidate_generator._belongs_to_customer(
        r, customer_id, "seva"
    )
]
purchased_keys = {
    engine._product_key(r) for r in purchased
    if engine._product_key(r)
}

print("\nPURCHASED KEYS:", sorted(purchased_keys))
print("SERVICE BASKETS:", len({r.get("service_id") for r in services}))

model = engine.cross_sell_ml_engine
model.fit(services)

print("\nMODEL STATE:")
for key, value in vars(model).items():
    print(key, "=", repr(value)[:1800])

try:
    predictions = model.recommend(purchased_keys)
    print("\nRAW ML PREDICTIONS:", predictions)
except Exception as exc:
    predictions = []
    print("\nPREDICTION ERROR:", type(exc).__name__, str(exc))

catalog_keys = {
    engine._product_key(p): p
    for p in products if engine._product_key(p)
}
excluded = set()
for records in (services, quotations, amcs):
    for record in records:
        if engine.candidate_generator._belongs_to_customer(
            record, customer_id, "seva"
        ):
            key = engine._product_key(record)
            if key:
                excluded.add(key)

print("\nCATALOG SIZE:", len(catalog_keys))
print("EXCLUDED KEYS:", sorted(excluded))
print("\nPREDICTION TARGET CHECK:")
for prediction in predictions or []:
    target = prediction.get("product_key")
    print({
        "target": target,
        "in_catalog": target in catalog_keys,
        "already_excluded": target in excluded,
        "prediction": prediction,
    })
