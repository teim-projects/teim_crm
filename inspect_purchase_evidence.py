from django.db import connection
from django.apps import apps

print("\n===== PRODUCT MODEL TABLE =====")
for model in apps.get_models():
    if model.__name__.lower() == "product":
        print("Model:", model._meta.label)
        print("Table:", model._meta.db_table)
        print("Primary key:", model._meta.pk.column)
        print("Product name field:", [
            (f.name, f.column) for f in model._meta.concrete_fields
            if "name" in f.name.lower()
        ])

from crmapp.product_intelligence.crm_adapters.seva.amc import SevaAMCAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

print("\n===== AMC ADAPTER RECORDS =====")
try:
    records = SevaAMCAdapter().get_universal_amc_products()
    print("Product-bearing records:", len(records))
    print("Distinct customers:", len({
        str(r.get("customer_id")) for r in records
        if r.get("customer_id") is not None
    }))
    for r in records[:15]:
        print({
            k: r.get(k) for k in (
                "customer_id", "product_id", "product_name",
                "visit_id", "service_date", "allocation_status",
                "crm_service_id", "complaint_service_id"
            ) if k in r
        })
except Exception as exc:
    print("AMC adapter error:", repr(exc))

print("\n===== INVOICE ADAPTER MAPPING =====")
try:
    adapter = SevaInvoiceAdapter()
    records = adapter.get_universal_invoice_products()
    print("Invoice item records:", len(records))
    print("Mapped product records:", sum(
        r.get("product_id") is not None for r in records
    ))
    print("Ambiguous names:", getattr(adapter, "ambiguous_names", []))
    print("Unmatched names:", getattr(adapter, "unmatched_names", []))
    for r in records:
        print({
            k: r.get(k) for k in (
                "customer_id", "product_id", "product_name",
                "transaction_id", "invoice_id", "product_mapping_status"
            ) if k in r
        })
except Exception as exc:
    print("Invoice adapter error:", repr(exc))
