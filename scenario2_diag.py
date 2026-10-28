import inspect
from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

print("ENGINE:", [n for n, f in inspect.getmembers(ProductRecommendationEngine, inspect.isfunction) if not n.startswith("_")])
for cls in (SevaServiceAdapter, SevaInvoiceAdapter):
    obj = cls()
    for n in dir(obj):
        if n.startswith("get_") and callable(getattr(obj, n)):
            try:
                rows = getattr(obj, n)()
                if isinstance(rows, (list, tuple)):
                    print(cls.__name__, n, "count=", len(rows),
                          "keys=", list(rows[0].keys()) if rows and isinstance(rows[0], dict) else [])
            except TypeError:
                continue
            except Exception as e:
                print(cls.__name__, n, "ERROR", type(e).__name__)
