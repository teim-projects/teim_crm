import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "teim_crm.settings")

import django
django.setup()
from collections import defaultdict
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

records = (
    SevaServiceAdapter().get_universal_service_products()
    + SevaInvoiceAdapter().get_universal_invoice_products()
)

baskets = defaultdict(set)
customers = defaultdict(set)

for r in records:
    customer = r.get("customer_id")
    basket = r.get("service_id") or r.get("transaction_id")
    product = r.get("product_key") or r.get("universal_product_key")

    if customer is not None and basket is not None and product is not None:
        key = (r.get("source_crm", ""), str(customer), str(basket))
        baskets[key].add(str(product))
        customers[str(customer)].add(str(basket))

eligible = {k: v for k, v in baskets.items() if len(v) >= 2}

print("Total purchase records:", len(records))
print("Customers with identified baskets:", len(customers))
print("Identified baskets:", len(baskets))
print("Multi-product baskets:", len(eligible))
print("Customers with multi-product baskets:",
      len({k[1] for k in eligible}))
print("Basket product counts:", sorted(len(v) for v in eligible.values()))
