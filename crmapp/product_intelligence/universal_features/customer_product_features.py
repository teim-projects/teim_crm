from collections import defaultdict


class UniversalCustomerProductFeatures:
    """
    CRM-independent customer-level product features.

    Products are identified by product_key so identical numeric
    product IDs from different CRMs remain separate.

    Supports older records that contain only product_id.
    """

    @staticmethod
    def _identity(record, source_crm=None):
        product_id = record.get("product_id")

        resolved_crm = record.get("source_crm") or source_crm
        if not resolved_crm:
            return None

        source_crm = str(resolved_crm).strip().lower()

        source_product_id = record.get(
            "source_product_id",
            product_id,
        )

        if source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()

        if not source_product_id:
            return None

        product_key = record.get("product_key")

        if not product_key:
            product_key = f"{source_crm}:{source_product_id}"

        return {
            "product_id": product_id,
            "source_crm": source_crm,
            "source_product_id": source_product_id,
            "product_key": str(product_key),
        }

    def build_customer_features(
        self,
        customer_id,
        service_products=None,
        quotation_products=None,
        amc_products=None,
        source_crm=None,
    ):
        source_crm = str(source_crm or "").strip().lower()
        if not source_crm:
            raise ValueError(
                "source_crm must be explicitly provided to build customer features."
            )

        service_products = service_products or []
        quotation_products = quotation_products or []
        amc_products = amc_products or []

        data_by_product = {}

        def belongs_to_customer(record):
            record_crm = str(
                record.get("source_crm") or source_crm
            ).strip().lower()

            return (
                record.get("customer_id") == customer_id
                and record_crm == source_crm
            )

        def get_data(identity):
            key = identity["product_key"]

            if key not in data_by_product:
                data_by_product[key] = {
                    **identity,
                    "service_count": 0,
                    "service_ids": set(),
                    "total_quantity": 0,
                    "quotation_count": 0,
                    "quotation_ids": set(),
                    "visit_count": 0,
                    "amc_ids": set(),
                    "visit_ids": set(),
                }

            return data_by_product[key]

        # Service history
        for record in service_products:
            if not belongs_to_customer(record):
                continue

            identity = self._identity(record, source_crm)

            if identity is None:
                continue

            data = get_data(identity)
            data["service_count"] += 1
            data["total_quantity"] += record.get("quantity") or 0

            service_id = record.get("service_id")
            if service_id is not None:
                data["service_ids"].add(service_id)

        # Quotation history
        for record in quotation_products:
            if not belongs_to_customer(record):
                continue

            identity = self._identity(record, source_crm)

            if identity is None:
                continue

            data = get_data(identity)
            data["quotation_count"] += 1

            quotation_id = record.get("quotation_id")
            if quotation_id is not None:
                data["quotation_ids"].add(quotation_id)

        # AMC history
        for record in amc_products:
            if not belongs_to_customer(record):
                continue

            identity = self._identity(record, source_crm)

            if identity is None:
                continue

            data = get_data(identity)
            data["visit_count"] += 1

            amc_id = record.get("amc_id")
            visit_id = record.get("visit_id")

            if amc_id is not None:
                data["amc_ids"].add(amc_id)

            if visit_id is not None:
                data["visit_ids"].add(visit_id)

        features = []

        for product_key in sorted(data_by_product):
            data = data_by_product[product_key]

            features.append({
                "customer_id": customer_id,
                "product_id": data["product_id"],
                "source_crm": data["source_crm"],
                "source_product_id": data["source_product_id"],
                "product_key": product_key,

                "service_count": data["service_count"],
                "service_unique_count": len(data["service_ids"]),
                "total_quantity": data["total_quantity"],

                "quotation_count": data["quotation_count"],
                "quotation_unique_count": len(data["quotation_ids"]),

                "amc_visit_count": data["visit_count"],
                "amc_count": len(data["amc_ids"]),
                "amc_visit_unique_count": len(data["visit_ids"]),
            })

        return features
