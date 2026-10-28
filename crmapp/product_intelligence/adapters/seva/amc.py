
from django.db import connection

from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class SevaAMCAdapter:
    """Convert SEVA AMC contracts and visit history into common records."""

    SOURCE_CRM = "seva"

    def get_universal_amc_products(self):
        """Return AMC visit-product history for product recommendations."""

        query = """
            SELECT
                v.amc_id,
                a.customer_id,
                v.product_id,
                v.id AS visit_id,
                v.service_date,
                v.allocation_status,
                v.crm_service_id,
                v.complaint_service_id,
                a.contract_number,
                a.start_date AS contract_start_date,
                a.end_date AS contract_end_date,
                a.status AS contract_status,
                a.is_active AS contract_is_active,
                a.renewal_status,
                a.renewal_requested_at,
                a.frequency AS contract_frequency,
                a.total_amount AS contract_total_amount,
                a.per_visit_amount AS contract_per_visit_amount
            FROM amc_amcservicevisit v
            INNER JOIN amc_amccontract a
                ON a.id = v.amc_id
            WHERE v.product_id IS NOT NULL
            ORDER BY v.amc_id, v.service_date, v.id
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = []

        for row in rows:
            (
                amc_id,
                customer_id,
                product_id,
                visit_id,
                service_date,
                allocation_status,
                crm_service_id,
                complaint_service_id,
                contract_number,
                contract_start_date,
                contract_end_date,
                contract_status,
                contract_is_active,
                renewal_status,
                renewal_requested_at,
                contract_frequency,
                contract_total_amount,
                contract_per_visit_amount,
            ) = row

            identity = UniversalProductIdentity.build(
                source_crm=self.SOURCE_CRM,
                source_product_id=product_id,
            )

            results.append({
                "amc_id": amc_id,
                "customer_id": customer_id,
                "product_id": product_id,
                "visit_id": visit_id,
                "service_date": service_date,
                "allocation_status": allocation_status,
                "crm_service_id": crm_service_id,
                "complaint_service_id": complaint_service_id,
                "contract_number": contract_number,
                "contract_start_date": contract_start_date,
                "contract_end_date": contract_end_date,
                "contract_status": contract_status,
                "contract_is_active": bool(contract_is_active),
                "renewal_status": renewal_status,
                "renewal_requested_at": renewal_requested_at,
                "contract_frequency": contract_frequency,
                "contract_total_amount": contract_total_amount,
                "contract_per_visit_amount": contract_per_visit_amount,
                **identity,
            })

        return results

    def get_universal_amc_contracts(self):
        """Return every AMC contract, including those without visits."""

        query = """
            SELECT
                id,
                customer_id,
                contract_number,
                start_date,
                end_date,
                status,
                is_active,
                renewal_status,
                renewal_requested_at,
                frequency,
                total_amount,
                per_visit_amount
            FROM amc_amccontract
            ORDER BY end_date, id
        """

        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = []

        for row in rows:
            (
                contract_id,
                customer_id,
                contract_number,
                start_date,
                end_date,
                status,
                is_active,
                renewal_status,
                renewal_requested_at,
                frequency,
                total_amount,
                per_visit_amount,
            ) = row

            results.append({
                "source_crm": self.SOURCE_CRM,
                "amc_id": contract_id,
                "contract_id": contract_id,
                "contract_key": f"{self.SOURCE_CRM}:{contract_id}",
                "customer_id": customer_id,
                "contract_number": contract_number,
                "contract_start_date": start_date,
                "contract_end_date": end_date,
                "contract_status": status,
                "contract_is_active": bool(is_active),
                "renewal_status": renewal_status,
                "renewal_requested_at": renewal_requested_at,
                "contract_frequency": frequency,
                "contract_total_amount": total_amount,
                "contract_per_visit_amount": per_visit_amount,
            })

        return results
