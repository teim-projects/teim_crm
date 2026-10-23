from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine

engine = ProductRecommendationEngine()
products = engine.product_adapter.get_universal_products()

for product in products:
    if product.get("product_key") in {"seva:54", "seva:63"}:
        print(
            product.get("product_key"),
            "|", product.get("product_name"),
            "| Category:", product.get("category"),
        )
