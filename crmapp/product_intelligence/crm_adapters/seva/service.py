
from crmapp.models import ServiceProduct
from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class SevaServiceAdapter:
    """Convert SEVA service-product history into common records."""

    SOURCE_CRM = "seva"

    def get_universal_service_products(self):
        records = ServiceProduct.objects.values(
            "product_id",
            "service_id",
            "service__customer_id",
            "quantity",
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

            results.append({
                "product_id": product_id,
                "customer_id": record["service__customer_id"],
                "service_id": record["service_id"],
                "quantity": record["quantity"],
                **identity,
            })

        return results
