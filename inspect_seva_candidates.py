from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine

engine = ProductRecommendationEngine()

products = engine.product_adapter.get_universal_products()
services = engine.service_adapter.get_universal_service_products()
quotations = engine.quotation_adapter.get_universal_quotation_products()
amc_records = engine.amc_adapter.get_universal_amc_products()

for customer_id in ("102", "35"):
    print(f"\n========== CUSTOMER {customer_id} ==========")

    candidates = engine.candidate_generator.generate(
        customer_id=customer_id,
        service_products=services,
        quotation_products=quotations,
        amc_products=amc_records,
        source_crm="seva",
        product_catalog=products,
        configured_relationships=engine.product_relationships,
    )

    for candidate in candidates:
        print(candidate)
