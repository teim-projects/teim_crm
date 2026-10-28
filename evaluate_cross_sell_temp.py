from pprint import pprint
from crmapp.product_intelligence.recommendations.cross_sell_evaluation import (
    evaluate_cross_sell_model,
    evaluate_cross_sell_model_by_basket,
)
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

records = (
    SevaServiceAdapter().get_universal_service_products()
    + SevaInvoiceAdapter().get_universal_invoice_products()
)

print("CUSTOMER-LEVEL EVALUATION")
try:
    pprint(evaluate_cross_sell_model(records))
except Exception as exc:
    print(type(exc).__name__, str(exc))

print("BASKET-LEVEL DIAGNOSTIC")
try:
    pprint(evaluate_cross_sell_model_by_basket(records))
except Exception as exc:
    print(type(exc).__name__, str(exc))
