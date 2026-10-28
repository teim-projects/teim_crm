"""SEVA service-product adapter; shared engine remains CRM-independent."""

from crmapp.models import ServiceProduct
from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class SevaServiceAdapter:
    SOURCE_CRM = "seva"

    def get_universal_service_products(self):
        records = ServiceProduct.objects.select_related(
            "product", "service", "service__customer"
        ).values(
            "product_id",
            "product__product_name",
            "product__category",
            "service_id",
            "service__customer_id",
            "service__service_date",
            "service__lead_date",
            "service__service_subject",
            "service__contract_type",
            "quantity",
            "price",
            "gst_percentage",
            "total_with_gst",
        )

        results = []
        for record in records:
            product_id = record["product_id"]
            if product_id is None:
                continue

            identity = UniversalProductIdentity.build(
                source_crm=self.SOURCE_CRM,
                source_product_id=product_id,
            )
            service_date = (
                record.get("service__service_date")
                or record.get("service__lead_date")
            )

            results.append({
                "source_crm": self.SOURCE_CRM,
                "history_source": "Service",
                "customer_id": record["service__customer_id"],
                "service_id": record["service_id"],
                "transaction_id": record["service_id"],
                "service_date": service_date,
                "activity_date": service_date,
                "service_subject": record["service__service_subject"],
                "contract_type": record["service__contract_type"],
                "product_id": product_id,
                "source_product_id": product_id,
                "product_name": record["product__product_name"],
                "category": record["product__category"],
                "quantity": record["quantity"],
                "unit_price": record["price"],
                "price": record["price"],
                "total": (
                    record["total_with_gst"]
                    if record["total_with_gst"] is not None
                    else (
                        record["price"] * record["quantity"]
                        * (1 + record["gst_percentage"] / 100)
                        if record["price"] is not None
                        and record["quantity"] is not None
                        and record["gst_percentage"] is not None
                        else None
                    )
                ),
                "total_with_gst": (
                    record["total_with_gst"]
                    if record["total_with_gst"] is not None
                    else (
                        record["price"] * record["quantity"]
                        * (1 + record["gst_percentage"] / 100)
                        if record["price"] is not None
                        and record["quantity"] is not None
                        and record["gst_percentage"] is not None
                        else None
                    )
                ),
                **identity,
            })

        return results
