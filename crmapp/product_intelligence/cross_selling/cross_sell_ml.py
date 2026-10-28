
from collections import defaultdict

import pandas as pd
from mlxtend.frequent_patterns import fpgrowth, association_rules


class CrossSellMLEngine:
    """CRM-independent FP-Growth cross-selling model."""

    def __init__(
        self,
        min_support=0.02,
        min_confidence=0.20,
        min_lift=1.0,
    ):
        if not 0 < min_support <= 1:
            raise ValueError("min_support must be in (0, 1].")
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be in [0, 1].")
        if min_lift < 0:
            raise ValueError("min_lift must be non-negative.")

        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.rules_ = pd.DataFrame()

    @staticmethod
    def _customer_key(record):
        crm = str(record.get("source_crm") or "unknown_crm").strip().lower()

        # Preserve CRM, customer, and transaction boundaries.
        customer_id = record.get("customer_id")
        customer = (
            str(customer_id).strip()
            if customer_id is not None and str(customer_id).strip()
            else None
        )

        service_id = record.get("service_id")
        if service_id is not None and str(service_id).strip():
            return crm, customer, "service", str(service_id).strip()

        transaction_id = record.get("transaction_id")
        if transaction_id is not None and str(transaction_id).strip():
            return crm, customer, "transaction", str(transaction_id).strip()

        # Never merge separate purchases into one basket. Records without a
        # transaction identifier cannot safely establish co-purchase evidence.
        return None

    @staticmethod
    def _product_key(record):
        product_id = record.get("product_id")
        crm = str(record.get("source_crm") or "unknown_crm").strip().lower()
        product_id = record.get("source_product_id", product_id)

        if product_id is None or not str(product_id).strip():
            return None

        return str(record.get("product_key") or f"{crm}:{product_id}")

    def fit(self, purchase_records, source_crm=None):
        if source_crm is not None:
            requested_crm = str(source_crm).strip().lower()
            purchase_records = [
                record for record in purchase_records
                if str(record.get("source_crm") or "unknown_crm").strip().lower()
                == requested_crm
            ]
        """Learn association rules from customer-product purchase history."""
        baskets = defaultdict(set)

        for record in purchase_records:
            if not isinstance(record, dict):
                continue

            product = self._product_key(record)
            if product is None:
                continue

            crm = str(
                record.get("source_crm") or source_crm or "unknown_crm"
            ).strip().lower()

            transaction_id = (
                record.get("service_id")
                or record.get("transaction_id")
                or record.get("quotation_id")
                or record.get("invoice_id")
            )

            if transaction_id is not None:
                basket_key = (crm, "transaction", str(transaction_id))
            else:
                customer = self._customer_key(record)
                if customer is None:
                    continue
                basket_key = (crm, "customer", str(customer))

            baskets[basket_key].add(product)

        if len(baskets) < 2:
            self.rules_ = pd.DataFrame()
            return self

        products = sorted({
            product
            for basket in baskets.values()
            for product in basket
        })

        if len(products) < 2:
            self.rules_ = pd.DataFrame()
            return self

        matrix = pd.DataFrame(
            [
                [product in baskets[customer] for product in products]
                for customer in baskets
            ],
            columns=products,
            dtype=bool,
        )

        frequent = fpgrowth(
            matrix,
            min_support=self.min_support,
            use_colnames=True,
        )

        if frequent.empty:
            self.rules_ = pd.DataFrame()
            return self

        rules = association_rules(
            frequent,
            metric="confidence",
            min_threshold=self.min_confidence,
        )

        if rules.empty:
            self.rules_ = rules
            return self

        self.rules_ = rules[
            (rules["lift"] >= self.min_lift)
            & (rules["antecedents"].map(len) == 1)
            & (rules["consequents"].map(len) == 1)
        ].copy()

        return self

    def recommend(self, purchased_product_keys, limit=10):
        """Recommend unseen products supported by learned association rules."""
        if limit < 1:
            return []

        purchased = {str(key) for key in purchased_product_keys}
        scores = {}

        if self.rules_.empty:
            return []

        for _, rule in self.rules_.iterrows():
            source = next(iter(rule["antecedents"]))
            target = next(iter(rule["consequents"]))

            if source not in purchased or target in purchased:
                continue

            item = scores.setdefault(
                target,
                {
                    "product_key": target,
                    "support": float(rule["support"]),
                    "confidence": float(rule["confidence"]),
                    "lift": float(rule["lift"]),
                    "source_products": [],
                },
            )

            item["source_products"].append(source)

            if (
                rule["confidence"] > item["confidence"]
                or (
                    rule["confidence"] == item["confidence"]
                    and rule["lift"] > item["lift"]
                )
            ):
                item["support"] = float(rule["support"])
                item["confidence"] = float(rule["confidence"])
                item["lift"] = float(rule["lift"])

        return sorted(
            scores.values(),
            key=lambda item: (
                item["confidence"],
                item["lift"],
                item["support"],
            ),
            reverse=True,
        )[:limit]
