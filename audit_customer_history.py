from collections import Counter
from crmapp.models import customer_details
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter

customers = list(customer_details.objects.only("id", "fullname", "customerid"))
pk_ids = {str(c.id): c for c in customers}
business_ids = {
    str(c.customerid).strip(): c
    for c in customers
    if c.customerid is not None and str(c.customerid).strip()
}

sources = {
    "SERVICE": SevaServiceAdapter().get_universal_service_products(),
    "INVOICE": SevaInvoiceAdapter().get_universal_invoice_products(),
}

print("CUSTOMERS:", len(customers))

for label, records in sources.items():
    pk_count = 0
    business_count = 0
    missing_count = 0
    unmatched = Counter()

    for record in records:
        raw = record.get("customer_id")
        if raw is None or not str(raw).strip():
            missing_count += 1
            continue

        key = str(raw).strip()
        if key in pk_ids:
            pk_count += 1
        elif key in business_ids:
            business_count += 1
        else:
            unmatched[key] += 1

    print(f"\n{label}: {len(records)} records")
    print("Matches by database ID:", pk_count)
    print("Matches by business customer ID:", business_count)
    print("Missing customer ID:", missing_count)
    print("Unmatched records:", sum(unmatched.values()))
    print("Unmatched ID samples:", list(unmatched.items())[:10])

    record_counts = Counter(
        str(r.get("customer_id")).strip()
        for r in records
        if r.get("customer_id") is not None
    )

    print("CUSTOMERS WITH NO MATCH BY DATABASE ID:")
    for c in customers:
        if record_counts[str(c.id)] == 0:
            print(
                f"id={c.id} | customerid={c.customerid!r} "
                f"| name={c.fullname!r}"
            )
