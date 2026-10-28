"""Held-out evaluation for the CRM-independent FP-Growth cross-sell model."""

from collections import defaultdict

from sklearn.model_selection import train_test_split

from .cross_sell_ml import CrossSellMLEngine


def evaluate_cross_sell_model(
    purchase_records,
    test_size=0.20,
    random_state=42,
    k=5,
    evaluation_mode="customer_level",
):
    """Evaluate top-k recommendations on held-out service/transaction baskets."""
    if evaluation_mode not in {"customer_level", "basket_level_diagnostic"}:
        raise ValueError("Unsupported evaluation_mode.")
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1.")

    if k < 1:
        raise ValueError("k must be at least 1.")

    records = [
        dict(record)
        for record in purchase_records
        if isinstance(record, dict)
    ]

    baskets = defaultdict(set)
    records_by_basket = defaultdict(list)
    customer_by_basket = {}

    for record in records:
        # Evaluation requires a genuine basket identifier. Do not merge
        # separate purchases merely because they share a customer.
        service_id = record.get("service_id")
        transaction_id = record.get("transaction_id")

        if service_id is not None and str(service_id).strip():
            basket_key = (
                str(record.get("source_crm") or "unknown_crm").strip().lower(),
                "service",
                str(service_id).strip(),
            )
        elif transaction_id is not None and str(transaction_id).strip():
            basket_key = (
                str(record.get("source_crm") or "unknown_crm").strip().lower(),
                "transaction",
                str(transaction_id).strip(),
            )
        else:
            continue

        product_key = CrossSellMLEngine._product_key(record)
        if product_key is None:
            continue

        baskets[basket_key].add(product_key)
        records_by_basket[basket_key].append(record)

        customer_id = record.get("customer_id")
        if customer_id is not None and str(customer_id).strip():
            customer_key = (
                str(record.get("source_crm") or "unknown_crm").strip().lower(),
                str(customer_id).strip(),
            )
            previous = customer_by_basket.get(basket_key)
            if previous is not None and previous != customer_key:
                raise ValueError(
                    "A service/transaction basket contains multiple customers."
                )
            customer_by_basket[basket_key] = customer_key

    baskets = {
        key: products
        for key, products in baskets.items()
        if len(products) >= 2
    }

    for key in list(records_by_basket):
        if key not in baskets:
            records_by_basket.pop(key, None)
            customer_by_basket.pop(key, None)

    if len(baskets) < 2:
        raise ValueError(
            "At least two multi-product service/transaction baskets "
            "are required for evaluation."
        )

    # Customer-level split prevents customer leakage. Diagnostic mode
    # intentionally splits individual baskets instead.
    baskets_by_customer = defaultdict(list)
    for basket_id in baskets:
        if evaluation_mode == "basket_level_diagnostic":
            group_key = ("diagnostic_basket", basket_id)
        else:
            group_key = customer_by_basket.get(
                basket_id, ("unknown_basket", basket_id)
            )
        baskets_by_customer[group_key].append(basket_id)

    group_ids = list(baskets_by_customer)
    if len(group_ids) < 2:
        raise ValueError(
            "At least two independent customer/basket groups are required "
            "for train/test evaluation."
        )

    train_groups, test_groups = train_test_split(
        group_ids,
        test_size=test_size,
        random_state=random_state,
        shuffle=True,
    )

    train_ids = [
        basket_id
        for group_id in train_groups
        for basket_id in baskets_by_customer[group_id]
    ]
    test_ids = [
        basket_id
        for group_id in test_groups
        for basket_id in baskets_by_customer[group_id]
    ]

    train_records = [
        record
        for basket_id in train_ids
        for record in records_by_basket[basket_id]
    ]

    model = CrossSellMLEngine()
    model.fit(train_records)

    hits = 0
    recommended_count = 0
    query_count = 0

    for basket_id in test_ids:
        products = sorted(baskets[basket_id])

        for target in products:
            context_products = [
                product for product in products if product != target
            ]

            predictions = model.recommend(context_products, limit=k)
            recommended_keys = [
                prediction["product_key"] for prediction in predictions
            ]

            query_count += 1
            recommended_count += len(recommended_keys)

            if target in recommended_keys:
                hits += 1

    if query_count == 0:
        raise ValueError("No eligible test queries were generated.")

    # Fixed-K Precision divides by the maximum recommendation slots,
    # including slots the model did not fill. Keep returned-item precision
    # separately for transparency. Each query has one held-out target.
    precision_at_k = hits / (query_count * k)
    returned_item_precision = (
        hits / recommended_count if recommended_count else 0.0
    )
    recall_at_k = hits / query_count
    hit_rate_at_k = hits / query_count

    f1_at_k = (
        2 * precision_at_k * recall_at_k
        / (precision_at_k + recall_at_k)
        if precision_at_k + recall_at_k
        else 0.0
    )

    return {
        "algorithm": "FP-Growth Association Rules",
        "evaluation_mode": evaluation_mode,
        "independent_customer_validation": evaluation_mode == "customer_level",
        "warning": (
            "Small held-out sample: interpret metrics cautiously."
            if len(test_ids) < 10 else ""
        ) if evaluation_mode == "customer_level" else
        "Diagnostic only: basket-level split does not ensure customer independence.",
        "train_baskets": len(train_ids),
        "test_baskets": len(test_ids),
        "evaluation_queries": query_count,
        f"precision_at_{k}": round(precision_at_k, 4),
        f"recall_at_{k}": round(recall_at_k, 4),
        f"hit_rate_at_{k}": round(hit_rate_at_k, 4),
        f"f1_at_{k}": round(f1_at_k, 4),
        "recommended_items": recommended_count,
        "successful_hits": hits,
        "precision_definition": "successful_hits / (evaluation_queries * K)",
        "returned_item_precision": round(returned_item_precision, 4),
        "metric_note": "Recall@K equals Hit Rate@K because each query has one held-out target; returned_item_precision uses only items actually returned.",
    }


def evaluate_cross_sell_model_by_basket(
    purchase_records,
    test_size=0.20,
    random_state=42,
    k=5,
):
    """Run a basket-level diagnostic; not independent customer validation."""
    return evaluate_cross_sell_model(
        purchase_records,
        test_size=test_size,
        random_state=random_state,
        k=k,
        evaluation_mode="basket_level_diagnostic",
    )

