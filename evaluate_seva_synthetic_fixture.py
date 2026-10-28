"""Evaluate FP-Growth against the generated synthetic SEVA basket fixtures.

This is a model/relationship-learning check, not yet a full adapter-to-engine test.
It reads JSON fixtures only and never writes to the database.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder


def _learn_rules(baskets, min_support=0.02, min_confidence=0.20):
    clean = [sorted(set(map(str, basket))) for basket in baskets if basket]
    if not clean:
        return []
    encoder = TransactionEncoder()
    matrix = pd.DataFrame(encoder.fit(clean).transform(clean), columns=encoder.columns_)
    itemsets = fpgrowth(matrix, min_support=min_support, use_colnames=True)
    if itemsets.empty:
        return []
    try:
        rules_df = association_rules(
            itemsets, metric="confidence", min_threshold=min_confidence
        )
    except TypeError:
        rules_df = association_rules(
            itemsets, num_itemsets=len(clean), metric="confidence",
            min_threshold=min_confidence,
        )
    rules = []
    for _, row in rules_df.iterrows():
        rules.append({
            "antecedents": set(row["antecedents"]),
            "consequents": set(row["consequents"]),
            "support": float(row["support"]),
            "confidence": float(row["confidence"]),
            "lift": float(row["lift"]),
        })
    return rules


def _recommend(context, rules, k=5):
    context = set(context)
    best = {}
    for rule in rules:
        if rule["antecedents"].issubset(context):
            for product in rule["consequents"] - context:
                rank = (rule["confidence"], rule["lift"], rule["support"])
                if product not in best or rank > best[product]:
                    best[product] = rank
    return [
        product for product, _ in sorted(
            best.items(), key=lambda pair: pair[1], reverse=True
        )[:k]
    ]


def _evaluate_completion(test_baskets, rules):
    queries = hits = recommended_items = 0
    for basket in test_baskets:
        if len(basket) < 2:
            continue
        # Hide each item in turn; the remaining items form the known basket context.
        for target in basket:
            context = [item for item in basket if item != target]
            if not context:
                continue
            recommendations = _recommend(context, rules, k=5)
            queries += 1
            recommended_items += len(recommendations)
            hits += int(target in recommendations)
    precision = hits / (5 * queries) if queries else 0.0
    recall = hits / queries if queries else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "evaluation_queries": queries,
        "successful_hits": hits,
        "recommended_items_total": recommended_items,
        "precision_at_5": round(precision, 4),
        "recall_at_5": round(recall, 4),
        "hit_rate_at_5": round(recall, 4),
        "f1_at_5": round(f1, 4),
    }


def _has_direct_rule(rules, antecedent, consequent):
    return any(
        rule["antecedents"] == {antecedent}
        and consequent in rule["consequents"]
        for rule in rules
    )


def evaluate_synthetic_fixture(
    fixture_dir="crmapp/product_intelligence/tests/fixtures/synthetic_data",
    test_fraction=0.20,
    min_support=0.02,
    min_confidence=0.20,
    seed=20261025,
):
    """Run customer-disjoint evaluation and an in-memory new-data learning check."""
    metadata_path = Path(fixture_dir) / "metadata.json"
    baskets_path = Path(fixture_dir) / "synthetic_purchase_baskets.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    records = json.loads(baskets_path.read_text(encoding="utf-8"))
    if not records:
        raise ValueError("Synthetic fixture has no purchase baskets.")
    if not all(row.get("is_synthetic") is True for row in records):
        raise ValueError("Refusing to evaluate records not explicitly marked synthetic.")

    grouped = defaultdict(list)
    for row in records:
        products = sorted(set(row.get("product_keys", [])))
        if products:
            grouped[row["customer_id"]].append(products)
    customers = sorted(grouped)
    if len(customers) < 10:
        raise ValueError("At least 10 synthetic customers are required.")

    # Deterministic customer-level split prevents the same customer's baskets crossing splits.
    import random
    rng = random.Random(seed)
    shuffled = customers[:]
    rng.shuffle(shuffled)
    test_count = max(1, round(len(shuffled) * test_fraction))
    test_customers = set(shuffled[:test_count])
    train_customers = set(shuffled[test_count:])
    train_baskets = [
        basket for customer in train_customers for basket in grouped[customer]
        if len(basket) > 1
    ]
    test_baskets = [
        basket for customer in test_customers for basket in grouped[customer]
        if len(basket) > 1
    ]
    if not train_baskets or not test_baskets:
        raise ValueError("Train/test split needs multi-product baskets on both sides.")

    baseline_rules = _learn_rules(train_baskets, min_support, min_confidence)
    baseline_metrics = _evaluate_completion(test_baskets, baseline_rules)

    # Controlled synthetic-only new-data experiment:
    # products exist in the observed SEVA universe, but this co-purchase pair is
    # deliberately planted ONLY in memory to test whether retraining learns new data.
    product_keys = {p for basket in grouped.values() for row in basket for p in row}
    new_pair = ("seva:10", "seva:13")
    if not set(new_pair).issubset(product_keys):
        raise ValueError(
            f"New-data probe requires products {new_pair}; found products: {sorted(product_keys)}"
        )
    augmented_train = [list(basket) for basket in train_baskets]
    # Add 40 repetitions to the training data only, not to the JSON fixtures or database.
    augmented_train.extend([list(new_pair) for _ in range(40)])
    updated_rules = _learn_rules(augmented_train, min_support, min_confidence)
    learned_new_pair = (
        _has_direct_rule(updated_rules, new_pair[0], new_pair[1])
        or _has_direct_rule(updated_rules, new_pair[1], new_pair[0])
    )
    recommendation_probe = _recommend([new_pair[0]], updated_rules, k=5)

    return {
        "algorithm": "FP-Growth association rules",
        "data_source": "synthetic_fixture_bootstrapped_from_real_SEVA_basket_templates",
        "database_modified": False,
        "warning": (
            "Synthetic-only validation. The planted new pair is a controlled test pattern, "
            "not a claim about real SEVA customer behavior or real-world accuracy."
        ),
        "source_metadata": {
            "real_source_purchase_records": metadata.get("real_source_purchase_records"),
            "real_source_baskets": metadata.get("real_source_baskets"),
            "real_source_multi_product_baskets": metadata.get("real_source_multi_product_baskets"),
        },
        "synthetic_counts": {
            "customers": len(customers),
            "baskets": len(records),
            "multi_product_baskets": sum(len(row.get("product_keys", [])) > 1 for row in records),
            "train_customers": len(train_customers),
            "test_customers": len(test_customers),
            "train_multi_product_baskets": len(train_baskets),
            "test_multi_product_baskets": len(test_baskets),
        },
        "baseline_training": {
            "association_rules_learned": len(baseline_rules),
            "metrics": baseline_metrics,
        },
        "new_data_retraining_probe": {
            "synthetic_only_planted_pair": list(new_pair),
            "additional_training_baskets_added_in_memory": 40,
            "association_rules_after_retraining": len(updated_rules),
            "new_pair_learned_after_retraining": learned_new_pair,
            "recommendation_for_first_pair_product": recommendation_probe,
            "passed": learned_new_pair and new_pair[1] in recommendation_probe,
        },
    }
