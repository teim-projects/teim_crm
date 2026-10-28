
from django.db import connection

from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class SevaQuotationAdapter:
    """Convert SEVA quotation-product history into common records."""

    SOURCE_CRM = "seva"

    def get_universal_quotation_products(self):
        query = """
            SELECT
                qs.quotation_management_id AS quotation_id,
                q.customer_id AS customer_id,
                qs.product_id AS product_id
            FROM crmapp_quotation_management_selected_services qs
            INNER JOIN crmapp_quotation_management q
                ON q.id = qs.quotation_management_id
            ORDER BY qs.quotation_management_id, qs.product_id
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = []

        for quotation_id, customer_id, product_id in rows:
            if product_id is None:
                continue

            identity = UniversalProductIdentity.build(
                source_crm=self.SOURCE_CRM,
                source_product_id=product_id,
            )

            results.append({
                "quotation_id": quotation_id,
                "customer_id": customer_id,
                "product_id": product_id,
                **identity,
            })

        return results
