
from collections import defaultdict


class ProductAssociationMetrics:
    """
    CRM-independent product association metrics.

    Products are identified by product_key, not numeric product_id.
    Calculates support, confidence, co-occurrence, and lift.
    """

    @staticmethod
    def _product_key(record):
        product_id = record.get("product_id")
        source_crm = str(
            record.get("source_crm") or "seva"
        ).strip().lower()

        source_product_id = record.get(
            "source_product_id", product_id
        )

        if source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()
        if not source_product_id:
            return None

        return str(
            record.get("product_key")
            or f"{source_crm}:{source_product_id}"
        )

    @staticmethod
    def _customer_key(record):
        customer_id = record.get("customer_id")
        source_crm = str(
            record.get("source_crm") or "seva"
        ).strip().lower()

        if customer_id is None:
            return None

        # Customer IDs are CRM-specific too.
        return source_crm, str(customer_id)

    def build(self, service_products):
        customer_products = defaultdict(set)
        product_customers = defaultdict(set)
        pair_counts = defaultdict(int)

        for record in service_products:
            customer_key = self._customer_key(record)
            product_key = self._product_key(record)

            if customer_key is None or product_key is None:
                continue

            customer_products[customer_key].add(product_key)
            product_customers[product_key].add(customer_key)

        for products in customer_products.values():
            products = sorted(products)

            for index, product_a in enumerate(products):
                for product_b in products[index + 1:]:
                    pair_counts[(product_a, product_b)] += 1

        total_customers = len(customer_products)
        product_support = {}

        for product_key, customers in product_customers.items():
            customer_count = len(customers)

            product_support[product_key] = {
                "customer_count": customer_count,
                "support": (
                    customer_count / total_customers
                    if total_customers
                    else 0
                ),
            }

        return {
            "customer_products": customer_products,
            "product_customers": product_customers,
            "pair_counts": pair_counts,
            "product_support": product_support,
            "total_customers": total_customers,
        }

    @staticmethod
    def get_pair_count(metrics, product_a, product_b):
        pair = tuple(sorted((product_a, product_b)))
        return metrics["pair_counts"].get(pair, 0)

    @staticmethod
    def get_support(metrics, product_key):
        return metrics["product_support"].get(
            product_key,
            {"customer_count": 0, "support": 0},
        )

    @classmethod
    def get_confidence(
        cls,
        metrics,
        source_product_key,
        candidate_product_key,
    ):
        source_customers = metrics["product_customers"].get(
            source_product_key,
            set(),
        )

        if not source_customers:
            return 0

        pair_count = cls.get_pair_count(
            metrics,
            source_product_key,
            candidate_product_key,
        )

        return pair_count / len(source_customers)

    @classmethod
    def get_lift(
        cls,
        metrics,
        source_product_key,
        candidate_product_key,
    ):
        source_support = cls.get_support(
            metrics, source_product_key
        )["support"]

        candidate_support = cls.get_support(
            metrics, candidate_product_key
        )["support"]

        pair_count = cls.get_pair_count(
            metrics,
            source_product_key,
            candidate_product_key,
        )

        total_customers = metrics["total_customers"]

        if total_customers == 0:
            return 0

        pair_support = pair_count / total_customers

        if source_support == 0 or candidate_support == 0:
            return 0

        return pair_support / (
            source_support * candidate_support
        )
