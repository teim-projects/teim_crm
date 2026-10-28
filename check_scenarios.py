import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
import django
django.setup()

from crmapp.product_intelligence.recommendations.recommendation_engine import ProductRecommendationEngine
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.quotation import SevaQuotationAdapter
from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

engine = ProductRecommendationEngine(
    source_crm="seva",
    product_adapter=SevaProductAdapter(),
    service_adapter=SevaServiceAdapter(),
    quotation_adapter=SevaQuotationAdapter(),
    amc_adapter=SevaAMCAdapter(),
    invoice_adapter=SevaInvoiceAdapter(),
)

for customer_id in [16, 27, 85, 100, 104, 109]:
    try:
        results = engine.recommend(customer_id)
        print(f"\nCUSTOMER {customer_id}: {len(results)} recommendations")
        for item in results[:5]:
            print(item)
    except Exception as exc:
        print(f"\nCUSTOMER {customer_id} ERROR: {type(exc).__name__}: {exc}")

