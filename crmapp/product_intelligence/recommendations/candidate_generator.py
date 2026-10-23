from collections import defaultdict


class ProductCandidateGenerator:
    """Generate CRM-independent product recommendation candidates."""

    def __init__(self, min_historical_support=2):
        if (
            not isinstance(min_historical_support, int)
            or isinstance(min_historical_support, bool)
            or min_historical_support < 1
        ):
            raise ValueError(
                "min_historical_support must be a positive integer."
            )
        self.min_historical_support = min_historical_support

    @staticmethod
    def _identity(record, source_crm=None):
        product_id = record.get("product_id")
        record_crm = str(record.get("source_crm") or source_crm or "").strip().lower()
        source_product_id = record.get("source_product_id", product_id)

        if not record_crm or source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()
        if not source_product_id:
            return None

        product_key = str(record.get("product_key") or "").strip().lower()
        if not product_key:
            product_key = f"{record_crm}:{source_product_id}"

        if not product_key.startswith(f"{record_crm}:"):
            return None

        return {
            "product_id": product_id,
            "source_crm": record_crm,
            "source_product_id": source_product_id,
            "product_key": product_key,
        }

    @staticmethod
    def _belongs_to_customer(record, customer_id, source_crm):
        record_crm = str(record.get("source_crm") or "").strip().lower()
        return (
            str(record.get("customer_id")) == str(customer_id)
            and record_crm == source_crm
        )

    @classmethod
    def build_product_relationships(cls, service_products):
        """Find products that occur together in the same service."""
        relationships = defaultdict(
            lambda: {"occurrence_count": 0, "source_services": set()}
        )
        service_products_map = defaultdict(set)

        for record in service_products:
            identity = cls._identity(record)
            service_id = record.get("service_id")

            if identity is None or service_id is None:
                continue

            service_key = (identity["source_crm"], str(service_id))
            service_products_map[service_key].add(identity["product_key"])

        for service_key, product_keys in service_products_map.items():
            product_keys = sorted(product_keys)

            for index, product_a in enumerate(product_keys):
                for product_b in product_keys[index + 1:]:
                    key = (product_a, product_b)
                    relationships[key]["occurrence_count"] += 1
                    relationships[key]["source_services"].add(service_key)

        return relationships

    def generate(
        self,
        customer_id,
        service_products=None,
        quotation_products=None,
        amc_products=None,
        source_crm=None,
        product_catalog=None,
        configured_relationships=None,
        allow_historical_cross_sell=True,
    ):
        """Generate repeat, cross-sell, and quotation candidates."""
        source_crm = str(source_crm or "").strip().lower()
        if not source_crm:
            raise ValueError("source_crm is required; CRM context cannot be inferred.")

        service_products = list(service_products or [])
        quotation_products = list(quotation_products or [])
        amc_products = list(amc_products or [])
        product_catalog = list(product_catalog or [])
        configured_relationships = list(configured_relationships or [])

        customer_service_products = [
            r for r in service_products
            if self._belongs_to_customer(r, customer_id, source_crm)
        ]
        customer_quotation_products = [
            r for r in quotation_products
            if self._belongs_to_customer(r, customer_id, source_crm)
        ]
        customer_amc_products = [
            r for r in amc_products
            if self._belongs_to_customer(r, customer_id, source_crm)
        ]
        crm_service_products = [
            r for r in service_products
            if str(r.get("source_crm") or "").strip().lower() == source_crm
        ]

        product_map = {}
        for record in product_catalog:
            identity = self._identity(record, source_crm)
            if identity is None or identity["source_crm"] != source_crm:
                continue
            product_map[identity["product_key"]] = {**record, **identity}

        # Compatibility: service records may also provide catalogue products.
        for record in crm_service_products:
            identity = self._identity(record)
            if identity is not None:
                product_map.setdefault(identity["product_key"], {**record, **identity})

        customer_products = {}

        def get_customer_product(identity):
            key = identity["product_key"]
            if key not in customer_products:
                customer_products[key] = {
                    **identity,
                    "service_count": 0,
                    "total_quantity": 0,
                    "service_ids": set(),
                    "amc_visit_count": 0,
                    "amc_ids": set(),
                }
            return customer_products[key]

        customer_service_keys = set()

        for record in customer_service_products:
            identity = self._identity(record)
            if identity is None:
                continue

            key = identity["product_key"]
            customer_service_keys.add(key)
            data = get_customer_product(identity)
            data["service_count"] += 1
            data["total_quantity"] += record.get("quantity") or 0

            service_id = record.get("service_id")
            if service_id is not None:
                data["service_ids"].add(service_id)

        for record in customer_amc_products:
            identity = self._identity(record)
            if identity is None:
                continue

            data = get_customer_product(identity)
            data["amc_visit_count"] += 1
            amc_id = record.get("amc_id")
            if amc_id is not None:
                data["amc_ids"].add(amc_id)

        quotation_keys = set()
        quotation_counts = defaultdict(int)
        counted_quotation_ids = defaultdict(set)

        for record in customer_quotation_products:
            identity = self._identity(record)
            if identity is None:
                continue

            key = identity["product_key"]
            quotation_keys.add(key)
            quotation_id = record.get("quotation_id")

            if quotation_id is None or str(quotation_id).strip() == "":
                quotation_counts[key] += 1
            elif quotation_id not in counted_quotation_ids[key]:
                counted_quotation_ids[key].add(quotation_id)
                quotation_counts[key] += 1

            get_customer_product(identity)

        existing_keys = set(customer_products)
        excluded_cross_sell_keys = existing_keys | quotation_keys
        candidates = {}

        for key, data in customer_products.items():
            if data["service_count"] == 0 and data["amc_visit_count"] == 0:
                continue

            candidates[key] = {
                **data,
                "candidate_type": "REPEAT",
                "amc_count": len(data["amc_ids"]),
                "source_products": [],
                "co_occurrence_count": 0,
                "quotation_interest": key in quotation_keys,
                "relationship_source": None,
                "relationship_strength": 0,
                "relationship_reason": None,
            }

        def add_cross_sell(
            source_key,
            target_key,
            relationship_source,
            relationship_strength=0,
            relationship_reason=None,
            co_occurrence_count=0,
        ):
            if source_key not in customer_service_keys:
                return
            if target_key in excluded_cross_sell_keys or target_key == source_key:
                return

            target = product_map.get(target_key)
            if target is None:
                return

            candidate = candidates.get(target_key)
            if candidate is not None and candidate["candidate_type"] != "CROSS_SELL":
                return

            if candidate is None:
                identity = self._identity(target, source_crm)
                if identity is None:
                    return

                candidate = {
                    **identity,
                    "candidate_type": "CROSS_SELL",
                    "service_count": 0,
                    "total_quantity": 0,
                    "amc_visit_count": 0,
                    "amc_count": 0,
                    "source_products": [],
                    "co_occurrence_count": 0,
                    "quotation_interest": False,
                    "relationship_source": relationship_source,
                    "relationship_strength": 0,
                    "relationship_reason": None,
                }
                candidates[target_key] = candidate

            if source_key not in candidate["source_products"]:
                candidate["source_products"].append(source_key)

            candidate["co_occurrence_count"] = max(
                candidate["co_occurrence_count"], co_occurrence_count
            )

            if relationship_source == "configured":
                candidate["relationship_source"] = "configured"
                candidate["relationship_strength"] = max(
                    candidate["relationship_strength"], relationship_strength
                )
                if relationship_reason:
                    candidate["relationship_reason"] = relationship_reason

        if allow_historical_cross_sell:
            relationships = self.build_product_relationships(crm_service_products)
            for (product_a, product_b), relationship in relationships.items():
                occurrence_count = relationship["occurrence_count"]
                if occurrence_count < self.min_historical_support:
                    continue

                if product_a in customer_service_keys:
                    add_cross_sell(
                        product_a, product_b, "historical",
                        co_occurrence_count=occurrence_count,
                    )
                if product_b in customer_service_keys:
                    add_cross_sell(
                        product_b, product_a, "historical",
                        co_occurrence_count=occurrence_count,
                    )

        for relationship in configured_relationships:
            if not isinstance(relationship, dict):
                continue

            source_key = str(relationship.get("source_product_key") or "").strip().lower()
            target_key = str(relationship.get("target_product_key") or "").strip().lower()

            if (
                not source_key.startswith(f"{source_crm}:")
                or not target_key.startswith(f"{source_crm}:")
            ):
                continue

            try:
                strength = float(relationship.get("strength", 50))
            except (TypeError, ValueError):
                continue

            if not 0 <= strength <= 100:
                continue

            add_cross_sell(
                source_key, target_key, "configured",
                relationship_strength=strength,
                relationship_reason=relationship.get("reason"),
            )

        for key in quotation_keys:
            if key in candidates:
                candidates[key]["quotation_interest"] = True
                continue

            identity = self._identity(customer_products[key], source_crm)
            candidates[key] = {
                **identity,
                "candidate_type": "QUOTATION",
                "service_count": 0,
                "total_quantity": 0,
                "amc_visit_count": 0,
                "amc_count": 0,
                "source_products": [],
                "co_occurrence_count": 0,
                "quotation_interest": True,
                "relationship_source": None,
                "relationship_strength": 0,
                "relationship_reason": None,
            }

        return [
            {
                **candidate,
                "product_id": candidate["product_id"],
                "product_key": key,
                "quotation_count": quotation_counts.get(key, 0),
            }
            for key, candidate in candidates.items()
        ]
