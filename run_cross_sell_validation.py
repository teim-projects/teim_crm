import contextlib
import io
import runpy
import statistics
import sys

RUNNER = "run_cross_sell_evaluation.py"

# Load the existing data preparation and evaluation imports.
captured = io.StringIO()
with contextlib.redirect_stdout(captured):
    namespace = runpy.run_path(RUNNER)

evaluate = namespace.get("evaluate_cross_sell_model")
if not callable(evaluate):
    raise RuntimeError(
        "Could not find evaluate_cross_sell_model in the existing runner."
    )

# Locate the already-prepared purchase records without inventing data.
candidates = []
for name, value in namespace.items():
    if not isinstance(value, list) or not value:
        continue
    if not all(isinstance(row, dict) for row in value):
        continue
    if any(
        any(k in row for k in (
            "product_id", "product_key", "universal_product_key"
        ))
        for row in value
    ):
        candidates.append((name, value))

if not candidates:
    print(captured.getvalue()[-3000:])
    raise RuntimeError(
        "Purchase records were not exposed by the existing runner. "
        "No evaluation was fabricated or reported."
    )

# Prefer the list containing the most prepared purchase records.
record_name, records = max(candidates, key=lambda item: len(item[1]))

def product_identity(row):
    for key in ("universal_product_key", "product_key", "source_product_key"):
        value = row.get(key)
        if value:
            return str(value).strip().lower()

    product_id = row.get("product_id")
    source_crm = str(row.get("source_crm") or "").strip().lower()
    if product_id is not None and source_crm:
        return f"{source_crm}:{product_id}"
    if product_id is not None:
        return str(product_id).strip().lower()
    return ""

def is_transport(row):
    identity = product_identity(row)
    return identity in {"seva:84", "84"}

eligible = [row for row in records if not is_transport(row)]

print("DATASET")
print("Record list:", record_name)
print("Original records:", len(records))
print("Excluded Transportation Charges records:", len(records) - len(eligible))
print("Eligible records:", len(eligible))
print("Evaluation: customer-level held-out splits")
print("K: 5")
print()

results = []
for seed in range(1, 21):
    try:
        result = evaluate(
            eligible,
            test_size=0.2,
            random_state=seed,
            k=5,
            split_by="customer",
        )
    except (ValueError, ZeroDivisionError) as exc:
        print(f"Split {seed}: skipped ({exc})")
        continue

    if not isinstance(result, dict):
        print(f"Split {seed}: unexpected result format; skipped")
        continue

    results.append(result)
    print(
        f"Split {seed}: "
        f"queries={result.get('evaluation_queries', 0)}, "
        f"precision@5={result.get('precision_at_5', 0)}, "
        f"recall@5={result.get('recall_at_5', 0)}, "
        f"hit_rate@5={result.get('hit_rate_at_5', 0)}, "
        f"hits={result.get('successful_hits', 0)}"
    )

print("\nSUMMARY")
print("Successful splits:", len(results))

for metric in ("precision_at_5", "recall_at_5", "hit_rate_at_5"):
    values = [
        float(row[metric])
        for row in results
        if row.get(metric) is not None
    ]
    if values:
        print(f"{metric} mean across splits: {statistics.mean(values):.4f}")

queries = sum(int(row.get("evaluation_queries", 0)) for row in results)
hits = sum(int(row.get("successful_hits", 0)) for row in results)
print("Total evaluation queries across splits:", queries)
print("Total successful hits across splits:", hits)

if queries == 0:
    print(
        "STATUS: INSUFFICIENT ELIGIBLE HELD-OUT QUERIES. "
        "Do not claim demonstrated recommendation performance."
    )
elif hits == 0:
    print(
        "STATUS: MODEL PERFORMANCE NOT DEMONSTRATED. "
        "Review eligible training history and rule coverage."
    )
else:
    print(
        "STATUS: Some held-out hits observed. "
        "Small-data results are exploratory, not proof of generalization."
    )
