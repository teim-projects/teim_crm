
from crmapp.models import customer_details
from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.invoice import SevaInvoiceAdapter
from crmapp.product_intelligence.crm_adapters.seva.product import SevaProductAdapter
from crmapp.product_intelligence.recommendations.cross_sell_ml import CrossSellMLEngine

customers = list(customer_details.objects.only("id", "fullname", "customerid"))
services = SevaServiceAdapter().get_universal_service_products()
invoices = SevaInvoiceAdapter().get_universal_invoice_products()
products = SevaProductAdapter().get_universal_products()

matched_invoices = [
    r for r in invoices
    if r.get("product_id") is not None
    and r.get("product_mapping_status") == "matched"
]
training = services + matched_invoices

def pkey(r):
    if r.get("product_key"):
        return str(r["product_key"]).strip()
    pid = r.get("source_product_id") or r.get("product_id")
    crm = r.get("source_crm")
    return f"{str(crm).strip().lower()}:{str(pid).strip()}" if crm and pid is not None else None

catalogue = {
    pkey(p): p for p in products
    if p.get("product_id") is not None and pkey(p)
}
model = CrossSellMLEngine().fit(training, source_crm="seva") if training else None

with_history, without_history = [], []
with_recs, without_recs = [], []

for c in customers:
    cid = str(c.id)
    history = [
        r for r in services + invoices
        if str(r.get("customer_id")) == cid
    ]
    (with_history if history else without_history).append(c)

    customer_records = [
        r for r in training
        if str(r.get("customer_id")) == cid and r.get("product_id") is not None
    ]
    purchased = {pkey(r) for r in customer_records if pkey(r)}
    recommendations = []

    if purchased and model:
        for pred in model.recommend(purchased, limit=10):
            key = str(pred.get("product_key", "")).strip()
            if key and key not in purchased and key in catalogue:
                recommendations.append((catalogue[key].get("product_name", key), pred))

    entry = (c, history, purchased, recommendations)
    (with_recs if recommendations else without_recs).append(entry)

print("\\n========== SEVA CUSTOMER REPORT ==========")
print("Total customers:", len(customers))
print("Customers with purchase history:", len(with_history))
print("Customers without purchase history:", len(without_history))
print("Customers with recommendations:", len(with_recs))
print("Customers without recommendations:", len(without_recs))
print("Service records:", len(services))
print("Invoice records:", len(invoices))
print("Matched invoice records used for ML:", len(matched_invoices))

for title, rows in [
    ("WITH PURCHASE HISTORY", with_history),
    ("WITHOUT PURCHASE HISTORY", without_history),
]:
    print(f"\\n--- {title} ({len(rows)}) ---")
    for c in rows:
        print(f"ID={c.id} | {c.fullname} | Code={c.customerid}")

for title, rows in [
    ("WITH RECOMMENDATIONS", with_recs),
    ("WITHOUT RECOMMENDATIONS", without_recs),
]:
    print(f"\\n--- {title} ({len(rows)}) ---")
    for c, history, purchased, recs in rows:
        print(
            f"ID={c.id} | {c.fullname} | "
            f"HistoryRecords={len(history)} | "
            f"LinkedProducts={len(purchased)} | Recommendations={len(recs)}"
        )
        for name, pred in recs:
            print(
                f"  - {name} | confidence={pred.get('confidence')} "
                f"| lift={pred.get('lift')}"
            )
print("\\n========== REPORT COMPLETE ==========")
