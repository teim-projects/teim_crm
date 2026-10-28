import json

from crmapp.product_intelligence.recommendations.recommendation_engine import (
    ProductRecommendationEngine,
)


class MemoryAdapter:
    def __init__(self, records):
        self.records = records

    def get_universal_products(self):
        return list(self.records)

    def get_universal_service_products(self):
        return list(self.records)

    def get_universal_quotation_products(self):
        return list(self.records)

    def get_universal_amc_products(self):
        return list(self.records)


def product(key, crm="seva"):
    source_id = key.split(":")[-1]
    return {
        "product_id": int(source_id),
        "source_product_id": source_id,
        "product_key": key,
        "source_crm": crm,
        "product_name": f"Synthetic product {source_id}",
        "active": True,
    }


def transaction(customer, basket, key, crm="seva"):
    source_id = key.split(":")[-1]
    return {
        "product_id": int(source_id),
        "source_product_id": source_id,
        "product_key": key,
        "source_crm": crm,
        "customer_id": customer,
        "service_id": basket,
        "quantity": 1,
    }


def flatten(value):
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(flatten(item))
        return result
    if isinstance(value, dict):
        if any(k in value for k in (
            "product_id", "source_product_id", "product_key"
        )):
            return [value]
        result = []
        for item in value.values():
            result.extend(flatten(item))
        return result
    return []


def recommendation_keys(result):
    keys = set()
    for item in flatten(result):
        key = item.get("product_key")
        if key:
            keys.add(str(key))
        source_id = item.get("source_product_id")
        if source_id is not None:
            keys.add(f"seva:{source_id}")
        product_id = item.get("product_id")
        if product_id is not None:
            keys.add(f"seva:{product_id}")
    return keys


def run_integration_check():
    catalogue = [product(f"seva:{i}") for i in range(1, 14)]

    # Customer being evaluated owns product 10.
    probe = transaction(
        "SYN-PROBE-001", "SYN-PROBE-BASKET", "seva:10"
    )

    # Training baseline: single-product baskets only.
    baseline_records = [
        transaction(f"SYN-BASE-{i:03}", f"BASE-BASKET-{i:03}", "seva:10")
        for i in range(40)
    ] + [probe]

    # Add 40 new synthetic baskets containing products 10 and 13.
    added_records = []
    for i in range(40):
        customer = f"SYN-PAIR-{i:03}"
        basket = f"PAIR-BASKET-{i:03}"
        added_records.extend([
            transaction(customer, basket, "seva:10"),
            transaction(customer, basket, "seva:13"),
        ])

    # Deliberately unrelated CRM data must not affect SEVA learning.
    foreign_records = [
        transaction(
            f"OTHER-{i:03}", f"OTHER-BASKET-{i:03}",
            "othercrm:13", crm="othercrm"
        )
        for i in range(40)
    ]

    def run_engine(service_records):
        engine = ProductRecommendationEngine(
            source_crm="seva",
            product_adapter=MemoryAdapter(catalogue),
            service_adapter=MemoryAdapter(service_records),
            quotation_adapter=MemoryAdapter([]),
            amc_adapter=MemoryAdapter([]),
        )
        return engine.recommend("SYN-PROBE-001")

    baseline = run_engine(baseline_records)
    retrained = run_engine(baseline_records + added_records)
    with_foreign = run_engine(
        baseline_records + added_records + foreign_records
    )

    baseline_keys = recommendation_keys(baseline)
    retrained_keys = recommendation_keys(retrained)
    foreign_keys = recommendation_keys(with_foreign)

    retrained_items = flatten(retrained)

    cross_sell_keys = {
        str(item["product_key"])
        for item in retrained_items
        if item.get("product_key")
        and (item.get("recommendation_type") or item.get("candidate_type"))
        == "CROSS_SELL"
    }
    repeat_keys = {
        str(item["product_key"])
        for item in retrained_items
        if item.get("product_key")
        and (item.get("recommendation_type") or item.get("candidate_type"))
        == "REPEAT"
    }

    checks = {
        "new_product_13_recommended_as_cross_sell": (
            "seva:13" in cross_sell_keys
        ),
        "owned_product_10_excluded_from_cross_sell": (
            "seva:10" not in cross_sell_keys
        ),
        "repeat_recommendation_remains_separate": (
            "seva:10" in repeat_keys
        ),
        "foreign_crm_does_not_change_recommendations": (
            retrained_keys == foreign_keys
        ),
        "recommendation_keys_before_retraining": sorted(baseline_keys),
        "recommendation_keys_after_retraining": sorted(retrained_keys),
        "database_modified": False,
    }
    checks["all_checks_passed"] = all([
        checks["new_product_13_recommended_as_cross_sell"],
        checks["owned_product_10_excluded_from_cross_sell"],
        checks["repeat_recommendation_remains_separate"],
        checks["foreign_crm_does_not_change_recommendations"],
    ])

    return checks


if __name__ == "__main__":
    print(json.dumps(run_integration_check(), indent=2, default=str))
