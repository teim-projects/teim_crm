from collections import defaultdict
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.quotation import SevaQuotationAdapter
from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter
from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine

products = SevaProductAdapter()
services = SevaServiceAdapter()
quotations = SevaQuotationAdapter()
amcs = SevaAMCAdapter()

customer_products = defaultdict(set)
for record in services.get_service_products():
    cid = record.get("customer_id")
    pk = record.get("product_key")
    if cid is not None and pk is not None:
        customer_products[cid].add(str(pk))

if not customer_products:
    print("No customer-linked service products found.")
else:
    cid = max(customer_products, key=lambda c: len(customer_products[c]))
    print("TEST CUSTOMER:", cid)
    print("HISTORICAL PRODUCTS:", sorted(customer_products[cid]))

    engine = ProductRecommendationEngine(
        source_crm="seva",
        product_adapter=products,
        service_adapter=services,
        quotation_adapter=quotations,
        amc_adapter=amcs,
    )
    results = engine.recommend(cid)
    print("RECOMMENDATION COUNT:", len(results))
    for item in results:
        print({
            "product_key": item.get("product_key"),
            "type": item.get("candidate_type"),
            "score": item.get("score"),
            "relationship_source": item.get("relationship_source"),
            "ml_confidence": item.get("ml_confidence"),
            "ml_lift": item.get("ml_lift"),
            "source_products": item.get("source_products"),
        })
