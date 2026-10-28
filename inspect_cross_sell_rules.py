from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine

records = SevaServiceAdapter().get_universal_service_products()
model = CrossSellMLEngine()
model.fit(records)

print("\nALGORITHM: FP-Growth")
print("REAL RECORDS:", len(records))

rules = model.rules_
if rules is None or rules.empty:
    print("No association rules learned from current real data.")
else:
    print("LEARNED RULES:", len(rules))
    columns = [
        c for c in ("antecedents", "consequents", "support", "confidence", "lift")
        if c in rules.columns
    ]
    print(rules[columns].to_string(index=False))
