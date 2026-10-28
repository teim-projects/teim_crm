import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from crmapp.models import Product, TaxInvoiceItem
from crmapp.product_intelligence.crm_adapters.seva.service import (
    SevaServiceAdapter,
)
from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)
from crmapp.product_intelligence.recommendations.cross_sell_evaluation import (
    evaluate_cross_sell_model,
)

records = list(SevaServiceAdapter().get_universal_service_products())

# Map invoice-line names to existing SEVA product IDs.
def normalize(value):
    return " ".join(str(value or "").casefold().split())

product_by_name = {
    normalize(product.product_name): product.product_id
    for product in Product.objects.all()
    if normalize(product.product_name)
}

invoice_lines_seen = 0
invoice_lines_added = 0
invoice_lines_unmapped = 0

for item in TaxInvoiceItem.objects.select_related("tax_invoice").all():
    invoice_lines_seen += 1
    invoice = item.tax_invoice

    customer_id = getattr(invoice, "customer_id", None)
    if customer_id is None:
        continue

    # Prefer a genuine product ID when the invoice line has one.
    raw_product_id = getattr(item, "product_id", None)
    if raw_product_id is not None and hasattr(raw_product_id, "product_id"):
        raw_product_id = raw_product_id.product_id

    if raw_product_id is not None:
        product_id = raw_product_id
        if not Product.objects.filter(product_id=product_id).exists():
            invoice_lines_unmapped += 1
            continue
    else:
        name = getattr(item, "product_name", None) or getattr(
            item, "description", None
        )
        product_id = product_by_name.get(normalize(name))
        if product_id is None:
            invoice_lines_unmapped += 1
            continue

    identity = UniversalProductIdentity.build(
        source_crm="seva",
        source_product_id=product_id,
    )

    records.append({
        "source_crm": "seva",
        "customer_id": customer_id,
        "transaction_id": f"invoice:{invoice.pk}",
        "product_id": product_id,
        "quantity": getattr(item, "quantity", None),
        **identity,
    })
    invoice_lines_added += 1

print("ALGORITHM: FP-Growth Association Rules")
print("SOURCE: SEVA service history + mapped invoice lines")
print("SERVICE RECORDS:", len(SevaServiceAdapter().get_universal_service_products()))
print("INVOICE LINES SCANNED:", invoice_lines_seen)
print("INVOICE LINES ADDED:", invoice_lines_added)
print("INVOICE LINES UNMAPPED:", invoice_lines_unmapped)
print("TOTAL EVALUATION RECORDS:", len(records))

for split_mode in ("customer", "basket"):
    try:
        results = evaluate_cross_sell_model(
            records,
            test_size=0.20,
            random_state=42,
            k=5,
            split_by=split_mode,
        )
        print(f"\n{'=' * 15} {split_mode.upper()}-LEVEL EVALUATION {'=' * 15}")
        for name, value in results.items():
            print(f"{name}: {value}")
    except (ValueError, ZeroDivisionError) as exc:
        print(f"\n{split_mode.upper()} EVALUATION LIMITATION: {exc}")

from crmapp.product_intelligence.recommendations.cross_sell_ml import (
    CrossSellMLEngine,
)

production_model = CrossSellMLEngine()
production_model.fit(records, source_crm="seva")

print("\\n===== FULL-DATA MODEL DIAGNOSTIC =====")
print("Eligible records used:", len(records))
print("Learned rules:", len(production_model.rules_))

if not production_model.rules_.empty:
    print(
        production_model.rules_[
            ["antecedents", "consequents", "support", "confidence", "lift"]
        ].to_string(index=False)
    )
else:
    print("No association rules meet the current thresholds.")

print("\\n===== PRODUCT IDENTITY AND BASKET CHECK =====")
for product_id in (32, 2, 1):
    product = Product.objects.filter(product_id=product_id).first()
    print(
        f"Product seva:{product_id}: "
        f"{getattr(product, 'product_name', 'NOT FOUND')}"
    )

    matches = []
    for record in records:
        key = CrossSellMLEngine._product_key(record)
        if key == f"seva:{product_id}":
            matches.append(record)

    print("Matching records:", len(matches))
    for record in matches[:10]:
        print({
            key: record.get(key)
            for key in (
                "customer_id", "service_id", "transaction_id",
                "invoice_id", "tax_invoice_id", "product_id",
                "product_key", "source_product_id"
            )
            if key in record
        })

