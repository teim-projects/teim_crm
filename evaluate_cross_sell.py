
from pathlib import Path
import csv
import json

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()


import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules
from crmapp.models import ServiceProduct


# ============================================================
# CONFIGURATION
# ============================================================

OUT = Path("reports/cross_sell_evaluation")
OUT.mkdir(parents=True, exist_ok=True)

MIN_SUPPORT = 0.05
MIN_CONFIDENCE = 0.20
MIN_LIFT = 1.0
TOP_K = 5
TRAIN_RATIO = 0.80


# ============================================================
# 1. EXTRACT REAL SERVICE TRANSACTIONS
# One service_id represents one product basket.
# ============================================================

rows = list(
    ServiceProduct.objects.filter(
        service__customer__isnull=False,
        service__service_date__isnull=False,
        product__isnull=False,
    )
    .values(
        "service_id",
        "service__customer_id",
        "service__service_date",
        "product_id",
        "product__product_name",
    )
    .order_by("service__service_date", "service_id")
)

baskets = {}
names = {}

for row in rows:
    service_id = row["service_id"]
    product_key = f"seva:{row['product_id']}"

    names[product_key] = row["product__product_name"]

    if service_id not in baskets:
        baskets[service_id] = {
            "service_id": service_id,
            "customer_id": row["service__customer_id"],
            "date": row["service__service_date"],
            "products": set(),
        }

    baskets[service_id]["products"].add(product_key)


transactions = sorted(
    baskets.values(),
    key=lambda item: (item["date"], item["service_id"]),
)

if len(transactions) < 2:
    raise SystemExit(
        "ERROR: At least two service transactions are required."
    )

dates = sorted({item["date"] for item in transactions})

if len(dates) < 2:
    raise SystemExit(
        "ERROR: At least two distinct service dates are required "
        "for chronological evaluation."
    )


# ============================================================
# 2. CHRONOLOGICAL TRAIN / TEST SPLIT
# Keep transactions from the same date together.
# ============================================================

cutoff_index = max(1, int(len(dates) * TRAIN_RATIO))
cutoff_index = min(cutoff_index, len(dates) - 1)
cutoff = dates[cutoff_index]

train = [
    item for item in transactions
    if item["date"] < cutoff
]

test = [
    item for item in transactions
    if item["date"] >= cutoff
]


# ============================================================
# 3. EXPORT TRANSACTIONS
# ============================================================

def export_transactions(filename, data):
    filepath = OUT / filename

    with filepath.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "service_id",
            "customer_id",
            "service_date",
            "product_keys",
            "product_names",
        ])

        for item in data:
            product_keys = sorted(item["products"])

            writer.writerow([
                item["service_id"],
                item["customer_id"],
                item["date"].isoformat(),
                ";".join(product_keys),
                ";".join(
                    names.get(key, key)
                    for key in product_keys
                ),
            ])


export_transactions("training_transactions.csv", train)
export_transactions("testing_transactions.csv", test)


# ============================================================
# 4. TRAIN APRIORI ASSOCIATION RULES
# Training transactions only; no test-data leakage.
# ============================================================

train_products = sorted({
    product
    for item in train
    for product in item["products"]
})

train_product_set = set(train_products)

rules = pd.DataFrame()

if len(train) >= 2 and len(train_products) >= 2:
    matrix = pd.DataFrame(
        [
            {
                product: product in item["products"]
                for product in train_products
            }
            for item in train
        ],
        dtype=bool,
    )

    frequent_itemsets = apriori(
        matrix,
        min_support=MIN_SUPPORT,
        use_colnames=True,
    )

    if not frequent_itemsets.empty:
        raw_rules = association_rules(
            frequent_itemsets,
            metric="confidence",
            min_threshold=MIN_CONFIDENCE,
        )

        if not raw_rules.empty:
            rules = raw_rules[
                (raw_rules["lift"] > MIN_LIFT)
                & (
                    raw_rules["antecedents"].map(len) == 1
                )
                & (
                    raw_rules["consequents"].map(len) == 1
                )
            ].copy()


# ============================================================
# 5. EXPORT LEARNED RULES
# ============================================================

rules_path = OUT / "learned_rules.csv"

with rules_path.open(
    "w", newline="", encoding="utf-8-sig"
) as file:
    writer = csv.writer(file)

    writer.writerow([
        "antecedent",
        "consequent",
        "support",
        "confidence",
        "lift",
    ])

    if not rules.empty:
        for _, rule in rules.iterrows():
            antecedent = next(iter(rule["antecedents"]))
            consequent = next(iter(rule["consequents"]))

            writer.writerow([
                f"{antecedent} ({names.get(antecedent, antecedent)})",
                f"{consequent} ({names.get(consequent, consequent)})",
                round(float(rule["support"]), 4),
                round(float(rule["confidence"]), 4),
                round(float(rule["lift"]), 4),
            ])


# ============================================================
# 6. BUILD CUSTOMER HISTORY FROM TRAINING DATA ONLY
# ============================================================

history = {}

for item in train:
    customer = str(item["customer_id"])

    history.setdefault(customer, set()).update(
        item["products"]
    )


# ============================================================
# 7. RECOMMENDATION FUNCTION
# Rank by confidence, lift, then support.
# Recommend only products not already purchased.
# ============================================================

def recommend(purchased, limit=TOP_K):
    if rules.empty or limit <= 0:
        return []

    scores = {}

    for _, rule in rules.iterrows():
        antecedent = next(iter(rule["antecedents"]))
        consequent = next(iter(rule["consequents"]))

        if antecedent not in purchased:
            continue

        if consequent in purchased:
            continue

        candidate_score = (
            float(rule["confidence"]),
            float(rule["lift"]),
            float(rule["support"]),
        )

        if (
            consequent not in scores
            or candidate_score > scores[consequent]
        ):
            scores[consequent] = candidate_score

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True,
    )

    return [
        product
        for product, _ in ranked[:limit]
    ]



# ============================================================
# 8. TRANSACTION-LEVEL CROSS-SELL EVALUATION
#
# Evaluate whether products in held-out baskets are predicted
# by association rules from earlier training baskets.
# This is NOT personalized customer-level evaluation.
# ============================================================

evaluated = 0
hits = 0

precision_values = []
recall_values = []

coverage_count = 0
skipped_no_known_products = 0
skipped_no_eligible_targets = 0

test_cases = len(test)

for item in test:
    # Products present in this test basket that the model
    # could have learned during training.
    known_products = item["products"] & train_product_set

    if not known_products:
        skipped_no_known_products += 1
        continue

    # Use products in the basket as the context for predicting
    # other products from that same basket.
    #
    # Each context product is considered separately so the
    # target product is never included in its own input.
    case_hits = 0
    case_predictions = 0
    case_relevant = 0

    for target in known_products:
        context = item["products"] - {target}

        if not context:
            continue

        # Only count targets for which at least one context
        # product has a learned association rule to the target.
        eligible_context = {
            product
            for product in context
            if product in train_product_set
        }

        if not eligible_context:
            continue

        target_is_predictable = False

        if not rules.empty:
            for _, rule in rules.iterrows():
                antecedent = next(iter(rule["antecedents"]))
                consequent = next(iter(rule["consequents"]))

                if (
                    antecedent in eligible_context
                    and consequent == target
                ):
                    target_is_predictable = True
                    break

        if target_is_predictable:
            case_relevant += 1

    if case_relevant == 0:
        skipped_no_eligible_targets += 1
        continue

    # For each test basket, evaluate predictions from its
    # observed products. The basket itself is used only for
    # offline evaluation, never to train the rules.
    predictions = set()

    for context_product in known_products:
        predictions.update(
            recommend({context_product}, TOP_K)
        )

    predictions -= item["products"]

    # Score only targets that are supported by at least one
    # learned association rule from a product in the basket.
    relevant = set()

    if not rules.empty:
        for _, rule in rules.iterrows():
            antecedent = next(iter(rule["antecedents"]))
            consequent = next(iter(rule["consequents"]))

            if (
                antecedent in known_products
                and consequent in item["products"]
                and consequent != antecedent
            ):
                relevant.add(consequent)

    if not relevant:
        skipped_no_eligible_targets += 1
        continue

    evaluated += 1

    # Keep the top K unique recommendations.
    ranked_predictions = []
    seen_predictions = set()

    for context_product in sorted(known_products):
        for product in recommend({context_product}, TOP_K):
            if (
                product not in item["products"]
                and product not in seen_predictions
            ):
                seen_predictions.add(product)
                ranked_predictions.append(product)

    ranked_predictions = ranked_predictions[:TOP_K]

    found = set(ranked_predictions) & relevant

    if ranked_predictions:
        coverage_count += 1

    if found:
        hits += 1

    precision_values.append(
        len(found) / TOP_K
    )

    recall_values.append(
        len(found) / len(relevant)
    )


# ============================================================
# 9. METRICS
# ============================================================

metrics = {
    "method": "Apriori association rules",
    "evaluation_type": "Transaction-level association evaluation",
    "source": "Real SEVA ServiceProduct records",
    "transaction_unit": "One service_id basket",
    "date_cutoff_exclusive_for_training": cutoff.isoformat(),
    "training_transactions": len(train),
    "testing_transactions": len(test),
    "training_product_rows": sum(
        len(item["products"]) for item in train
    ),
    "testing_product_rows": sum(
        len(item["products"]) for item in test
    ),
    "distinct_training_products": len(train_products),
    "min_support": MIN_SUPPORT,
    "min_confidence": MIN_CONFIDENCE,
    "min_lift_exclusive": MIN_LIFT,
    "learned_rule_count": len(rules),
    "test_cases": test_cases,
    "evaluable_test_cases": evaluated,
    "skipped_no_known_training_products": skipped_no_known_products,
    "skipped_no_supported_targets": skipped_no_eligible_targets,
    "recommendation_coverage_on_evaluable_cases": (
        coverage_count / evaluated if evaluated else None
    ),
    "hit_rate_at_5": (
        hits / evaluated if evaluated else None
    ),
    "precision_at_5": (
        sum(precision_values) / evaluated if evaluated else None
    ),
    "recall_at_5": (
        sum(recall_values) / evaluated if evaluated else None
    ),
    "evaluation_warning": (
        "Transaction-level offline evaluation is not personalized "
        "customer-level evaluation. Metrics may be unstable with "
        "few test baskets and measure historical association "
        "prediction, not guaranteed future business performance."
    ),
}

metrics_path = OUT / "evaluation_metrics.json"

metrics_path.write_text(
    json.dumps(metrics, indent=2),
    encoding="utf-8",
)

print("\n========== CROSS-SELL MODEL EVALUATION ==========")
print(json.dumps(metrics, indent=2))

print("\n========== EVALUATION DIAGNOSTICS ==========")
print("Total test baskets:", test_cases)
print("Skipped: no known training products:", skipped_no_known_products)
print("Skipped: no supported targets:", skipped_no_eligible_targets)
print("Evaluable test baskets:", evaluated)

print("\nReport files saved in:", OUT.resolve())
print(" - training_transactions.csv")
print(" - testing_transactions.csv")
print(" - learned_rules.csv")
print(" - evaluation_metrics.json")

# ============================================================
# 10. PRINT RESULTS
# ============================================================
