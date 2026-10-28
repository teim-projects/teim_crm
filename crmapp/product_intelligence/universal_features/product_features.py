
from collections import defaultdict

from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class UniversalProductFeatures:
    """
    CRM-independent product feature builder.

    Aggregates service, quotation, and AMC history using CRM-aware
    product keys so products from different CRMs are not mixed.
    """

    @staticmethod
    def _get_product_key(record):
        """Return a CRM-aware key, including for legacy records."""
        product_id = record.get("product_id")

        if product_id is None:
            return None

        existing_key = record.get("product_key")
        if existing_key:
            return existing_key

        identity = UniversalProductIdentity.build(
            source_crm=record.get("source_crm"),
            source_product_id=record.get(
                "source_product_id",
                product_id,
            ),
        )
        return identity["product_key"]

    @staticmethod
    def _empty_service_data():
        return {
            "usage_count": 0,
            "customer_ids": set(),
            "service_ids": set(),
            "total_quantity": 0,
        }

    @staticmethod
    def _empty_quotation_data():
        return {
            "quotation_count": 0,
            "customer_ids": set(),
            "quotation_ids": set(),
        }

    @staticmethod
    def _empty_amc_data():
        return {
            "visit_count": 0,
            "customer_ids": set(),
            "amc_ids": set(),
        }

    def build_product_features(
        self,
        products,
        service_products=None,
        quotation_products=None,
        amc_products=None,
    ):
        service_products = service_products or []
        quotation_products = quotation_products or []
        amc_products = amc_products or []

        service_usage = defaultdict(self._empty_service_data)
        quotation_usage = defaultdict(self._empty_quotation_data)
        amc_usage = defaultdict(self._empty_amc_data)

        # Aggregate service history by CRM-aware product key.
        for record in service_products:
            product_key = self._get_product_key(record)
            if product_key is None:
                continue

            data = service_usage[product_key]
            data["usage_count"] += 1

            customer_id = record.get("customer_id")
            service_id = record.get("service_id")
            quantity = record.get("quantity") or 0

            if customer_id is not None:
                data["customer_ids"].add(customer_id)

            if service_id is not None:
                data["service_ids"].add(service_id)

            data["total_quantity"] += quantity

        # Aggregate quotation history by CRM-aware product key.
        for record in quotation_products:
            product_key = self._get_product_key(record)
            if product_key is None:
                continue

            data = quotation_usage[product_key]
            data["quotation_count"] += 1

            customer_id = record.get("customer_id")
            quotation_id = record.get("quotation_id")

            if customer_id is not None:
                data["customer_ids"].add(customer_id)

            if quotation_id is not None:
                data["quotation_ids"].add(quotation_id)

        # Aggregate AMC visit history by CRM-aware product key.
        for record in amc_products:
            product_key = self._get_product_key(record)
            if product_key is None:
                continue

            data = amc_usage[product_key]
            data["visit_count"] += 1

            customer_id = record.get("customer_id")
            amc_id = record.get("amc_id")

            if customer_id is not None:
                data["customer_ids"].add(customer_id)

            if amc_id is not None:
                data["amc_ids"].add(amc_id)

        # Build one feature record per product.
        features = []

        for product in products:
            product_id = product.get("product_id")
            product_key = self._get_product_key(product)

            if product_key is None:
                continue

            service_data = service_usage[product_key]
            quotation_data = quotation_usage[product_key]
            amc_data = amc_usage[product_key]

            identity = UniversalProductIdentity.build(
                source_crm=product.get("source_crm"),
                source_product_id=product.get(
                    "source_product_id",
                    product_id,
                ),
            )

            features.append({
                # Existing fields retained for compatibility.
                "product_id": product_id,
                "product_name": product.get("product_name"),
                "category": product.get("category"),

                # CRM-aware identity.
                **identity,

                # Service evidence.
                "service_usage_count": service_data["usage_count"],
                "service_customer_count": len(
                    service_data["customer_ids"]
                ),
                "service_count": len(service_data["service_ids"]),
                "total_quantity": service_data["total_quantity"],

                # Quotation evidence.
                "quotation_count": quotation_data["quotation_count"],
                "quotation_customer_count": len(
                    quotation_data["customer_ids"]
                ),
                "quotation_unique_count": len(
                    quotation_data["quotation_ids"]
                ),

                # AMC evidence.
                "amc_visit_count": amc_data["visit_count"],
                "amc_customer_count": len(amc_data["customer_ids"]),
                "amc_count": len(amc_data["amc_ids"]),
            })

        return features
