from collections import defaultdict
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine

records = SevaServiceAdapter().get_universal_service_products()
model = CrossSellMLEngine().fit(records)

baskets = defaultdict(set)
customer_history = defaultdict(set)

for record in records:
    key = model._product_key(record)
    customer = record.get("customer_id")
    service = record.get("service_id")
    if key and customer is not None:
        customer_history[str(customer)].add(key)
    if key and customer is not None and service is not None:
        baskets[(str(customer), str(service))].add(key)

print("LEARNED RULES:", len(model.rules_))
found = 0

for (customer, service), basket in sorted(baskets.items()):
    predictions = model.recommend(basket)
    new_items = [
        p for p in predictions
        if p["product_key"] not in customer_history[customer]
    ]
    if predictions:
        print({
            "customer": customer,
            "service": service,
            "basket": sorted(basket),
            "predictions": predictions,
            "new_to_customer": new_items,
        })
        found += 1

print("SERVICE BASKETS WITH ML PREDICTIONS:", found)
