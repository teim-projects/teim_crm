import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teim_crm.settings")

import django
django.setup()

from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter
from crmapp.product_intelligence.recommendations.cross_sell_evaluation import (
    evaluate_cross_sell_model,
    evaluate_cross_sell_model_by_basket,
)
import json

records = SevaServiceAdapter().get_universal_service_products()
records += SevaInvoiceAdapter().get_universal_invoice_products()

for name, fn in [
    ("CUSTOMER LEVEL", evaluate_cross_sell_model),
    ("BASKET DIAGNOSTIC", evaluate_cross_sell_model_by_basket),
]:
    print("\n===", name, "===")
    try:
        print(json.dumps(fn(records), indent=2, default=str))
    except Exception as e:
        print(type(e).__name__, str(e))
