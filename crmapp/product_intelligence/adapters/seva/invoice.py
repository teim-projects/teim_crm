"""SEVA invoice adapter for real invoice-backed purchase history."""

import re

from crmapp.models import Product, TaxInvoiceItem
from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class SevaInvoiceAdapter:
    SOURCE_CRM = "seva"

    @staticmethod
    def _normalize_name(value):
        return re.sub(r"\\s+", " ", str(value or "")).strip().casefold()

    def get_universal_invoice_products(self):
        catalogue = {}
        for product in Product.objects.all().only(
            "product_id", "product_name", "category"
        ):
            key = self._normalize_name(product.product_name)
            if key:
                catalogue.setdefault(key, []).append(product)

        results = []
        self.unmatched_names = []
        self.ambiguous_names = []

        items = TaxInvoiceItem.objects.select_related(
            "tax_invoice", "tax_invoice__customer"
        ).all()

        for item in items:
            invoice = item.tax_invoice
            name = str(item.product_name or "").strip()
            matches = catalogue.get(self._normalize_name(name), [])

            product = matches[0] if len(matches) == 1 else None
            if len(matches) > 1:
                self.ambiguous_names.append(name)
            elif not matches:
                self.unmatched_names.append(name)

            record = {
                "source_crm": self.SOURCE_CRM,
                "history_source": "Invoice",
                "customer_id": invoice.customer_id,
                "transaction_id": item.tax_invoice_id,
                "invoice_id": item.tax_invoice_id,
                "invoice_number": invoice.tax_invoice_no,
                "invoice_date": invoice.dated or invoice.created_at,
                "activity_date": invoice.dated or invoice.created_at,
                "product_id": product.product_id if product else None,
                "source_product_id": product.product_id if product else None,
                "product_name": (
                    product.product_name if product else name
                ),
                "category": (
            product.category
            if product
            else (
                matches[0].category
                if matches and all(
                    candidate.category == matches[0].category
                    for candidate in matches
                )
                else ""
            )
        ),
                "quantity": item.quantity,
                "unit_price": item.price,
                "price": item.price,
                "total": item.total,
                "product_mapping_status": (
                    "matched" if product else
                    "ambiguous" if len(matches) > 1 else "unmatched"
                ),
            }

            if product:
                record.update(UniversalProductIdentity.build(
                    source_crm=self.SOURCE_CRM,
                    source_product_id=product.product_id,
                ))

            results.append(record)

        return results
