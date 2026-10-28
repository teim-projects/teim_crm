from collections import Counter
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.quotation import SevaQuotationAdapter
from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter

service = SevaServiceAdapter().get_universal_service_products()
invoice_adapter = SevaInvoiceAdapter()
invoice = invoice_adapter.get_universal_invoice_products()
quotation = SevaQuotationAdapter().get_universal_quotation_products()
amc_adapter = SevaAMCAdapter()
amc = amc_adapter.get_universal_amc_products()
contracts = amc_adapter.get_universal_amc_contracts()

def customers(rows):
    return {str(r["customer_id"]) for r in rows
            if r.get("customer_id") is not None}

def baskets(rows, key):
    grouped = {}
    for r in rows:
        customer = r.get("customer_id")
        transaction = r.get(key)
        product = r.get("product_key")
        if customer is None or transaction is None or product is None:
            continue
        grouped.setdefault((str(customer), str(transaction)), set()).add(product)
    sizes = Counter(len(v) for v in grouped.values())
    return len(grouped), dict(sorted(sizes.items()))

matched = [r for r in invoice if r.get("product_mapping_status") == "matched"]
print("\n===== SOURCE COUNTS =====")
for name, rows in [
    ("Service products", service),
    ("Invoice items", invoice),
    ("Matched invoice items", matched),
    ("Quotation products", quotation),
    ("AMC visit products", amc),
    ("AMC contracts", contracts),
]:
    print(f"{name}: {len(rows)} | customers: {len(customers(rows))}")

print("\n===== CUSTOMER COVERAGE =====")
sets = {
    "Service": customers(service),
    "Invoice": customers(matched),
    "Quotation": customers(quotation),
    "AMC visits": customers(amc),
    "AMC contracts": customers(contracts),
}
for name, ids in sets.items():
    print(f"{name}: {len(ids)} customers")
print("Invoice/Service overlap:", len(sets["Invoice"] & sets["Service"]))
print("Quotation-only customers:", len(sets["Quotation"] - sets["Service"] - sets["Invoice"]))
print("AMC-visit-only customers:", len(sets["AMC visits"] - sets["Service"] - sets["Invoice"]))

print("\n===== TRANSACTION BASKETS =====")
for name, rows, key in [
    ("Service", service, "transaction_id"),
    ("Matched invoice", matched, "transaction_id"),
    ("Quotation (NOT proof of purchase)", quotation, "quotation_id"),
    ("AMC visits", amc, "visit_id"),
]:
    print(name, baskets(rows, key))

print("\n===== INVOICE MAPPING =====")
print("Unmatched names:", len(invoice_adapter.unmatched_names))
print("Ambiguous names:", len(invoice_adapter.ambiguous_names))
print("Unmatched examples:", invoice_adapter.unmatched_names[:20])
print("Ambiguous examples:", invoice_adapter.ambiguous_names[:20])

print("\n===== AMC OVERLAP CHECK =====")
service_ids = {str(r.get("service_id")) for r in service if r.get("service_id") is not None}
linked_ids = {str(r.get("crm_service_id")) for r in amc if r.get("crm_service_id") is not None}
print("AMC visits linked to CRM service IDs:", len(linked_ids))
print("Distinct linked IDs also in ServiceProduct:", len(linked_ids & service_ids))
print("AMC visits without CRM service link:", sum(not r.get("crm_service_id") for r in amc))
