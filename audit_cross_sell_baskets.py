from collections import defaultdict, Counter

from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

services = SevaServiceAdapter().get_universal_service_products()
invoice_adapter = SevaInvoiceAdapter()
invoices = invoice_adapter.get_universal_invoice_products()
invoices = [
    r for r in invoices
    if r.get("product_id") is not None
    and r.get("product_mapping_status") == "matched"
]

def audit(label, records, transaction_field):
    baskets = defaultdict(set)
    customers = defaultdict(set)

    for r in records:
        tx = r.get(transaction_field)
        customer = r.get("customer_id")
        product = r.get("product_id")
        if tx is None or customer is None or product is None:
            continue
        baskets[(customer, tx)].add(product)
        customers[customer].add(product)

    sizes = Counter(len(products) for products in baskets.values())
    multi = {key: value for key, value in baskets.items() if len(value) >= 2}

    print(f"\n===== {label} =====")
    print("Valid records:", sum(len(v) for v in baskets.values()))
    print("Customers:", len(customers))
    print("Baskets:", len(baskets))
    print("Basket sizes:", dict(sorted(sizes.items())))
    print("Multi-product baskets:", len(multi))
    print("Distinct products in multi-product baskets:",
          len(set().union(*multi.values())) if multi else 0)
    for (customer, tx), products in list(multi.items())[:10]:
        print("Customer:", customer, "| Transaction:", tx,
              "| Products:", sorted(products))

    return customers, baskets

service_customers, service_baskets = audit(
    "SERVICE TRANSACTIONS", services, "transaction_id"
)
invoice_customers, invoice_baskets = audit(
    "MATCHED INVOICE TRANSACTIONS", invoices, "transaction_id"
)

print("\n===== CUSTOMER OVERLAP =====")
print("Service customers:", len(service_customers))
print("Invoice customers:", len(invoice_customers))
print("Shared customers:", len(set(service_customers) & set(invoice_customers)))
print("Combined unique customers:",
      len(set(service_customers) | set(invoice_customers)))

print("\nAudit only; no database changes made.")
