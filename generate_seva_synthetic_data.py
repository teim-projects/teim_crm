"""Generate isolated synthetic SEVA purchase fixtures from observed basket patterns.

This script reads real SEVA service-product records through the adapter and writes
synthetic JSON fixtures only. It NEVER inserts or updates database records.

Synthetic baskets intentionally oversample observed multi-product templates so the
recommendation pipeline has enough examples to validate learning behavior. Therefore,
synthetic basket frequencies are NOT estimates of real customer behavior.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


def load_real_basket_templates():
    from crmapp.product_intelligence.crm_adapters.seva.service import SevaServiceAdapter

    records = [
        dict(record)
        for record in SevaServiceAdapter().get_universal_service_products()
    ]
    baskets = defaultdict(set)
    for record in records:
        service_id = record.get("service_id")
        product_key = record.get("product_key")
        if service_id is None or not product_key:
            continue
        crm = record.get("source_crm") or "seva"
        baskets[(str(crm), str(service_id))].add(str(product_key))

    templates = [sorted(items) for items in baskets.values() if items]
    multi_templates = [items for items in templates if len(items) > 1]
    single_templates = [items for items in templates if len(items) == 1]
    if not multi_templates:
        raise RuntimeError(
            "No real multi-product baskets found. Cannot build pattern-based fixtures."
        )
    return records, templates, multi_templates, single_templates


def generate_fixtures(
    output_dir,
    customers=120,
    baskets_per_customer=8,
    multi_product_rate=0.75,
    seed=20261025,
):
    if customers < 10:
        raise ValueError("customers must be >= 10")
    if baskets_per_customer < 1:
        raise ValueError("baskets_per_customer must be >= 1")
    if not 0.0 <= multi_product_rate <= 1.0:
        raise ValueError("multi_product_rate must be between 0 and 1")

    records, templates, multi_templates, single_templates = load_real_basket_templates()
    rng = random.Random(seed)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    product_keys = sorted(
        {product for basket in templates for product in basket}
    )
    customers_data = [
        {
            "customer_id": f"SYN-CUST-{i:04d}",
            "source_crm": "seva",
            "is_synthetic": True,
        }
        for i in range(1, customers + 1)
    ]
    products_data = [
        {
            "product_key": key,
            "source_crm": "seva",
            "is_synthetic": True,
            "source": "observed_real_product_universe",
        }
        for key in product_keys
    ]

    baskets_data = []
    observed_multi_pattern_counts = Counter(tuple(items) for items in multi_templates)
    start_date = date(2026, 1, 1)
    basket_number = 0

    for customer_index in range(1, customers + 1):
        customer_id = f"SYN-CUST-{customer_index:04d}"
        for visit_index in range(1, baskets_per_customer + 1):
            basket_number += 1
            use_multi = (
                bool(multi_templates)
                and (not single_templates or rng.random() < multi_product_rate)
            )
            if use_multi:
                # Sample observed multi-product basket templates with replacement.
                products = list(rng.choice(multi_templates))
                basket_type = "pattern_enriched_multi_product"
            else:
                products = list(rng.choice(single_templates)) if single_templates else list(rng.choice(multi_templates))
                basket_type = "single_product" if len(products) == 1 else "pattern_enriched_multi_product"

            # Only remove an item occasionally from baskets with 3+ products.
            # No new product pair is invented by this operation.
            if len(products) >= 3 and rng.random() < 0.08:
                products.pop(rng.randrange(len(products)))

            baskets_data.append(
                {
                    "basket_id": f"SYN-BASKET-{basket_number:06d}",
                    "customer_id": customer_id,
                    "transaction_id": f"SYN-TXN-{basket_number:06d}",
                    "service_id": f"SYN-SERVICE-{basket_number:06d}",
                    "source_crm": "seva",
                    "purchase_date": (start_date + timedelta(days=basket_number % 270)).isoformat(),
                    "product_keys": sorted(set(products)),
                    "is_synthetic": True,
                    "generation_type": basket_type,
                }
            )

    metadata = {
        "dataset_name": "SEVA synthetic cross-sell validation fixtures",
        "is_synthetic": True,
        "database_modified": False,
        "real_source_purchase_records": len(records),
        "real_source_baskets": len(templates),
        "real_source_multi_product_baskets": len(multi_templates),
        "real_source_single_product_baskets": len(single_templates),
        "real_observed_multi_product_templates": [
            {"product_keys": list(items), "observed_baskets": count}
            for items, count in observed_multi_pattern_counts.items()
        ],
        "synthetic_customers": len(customers_data),
        "synthetic_products": len(products_data),
        "synthetic_baskets": len(baskets_data),
        "synthetic_multi_product_rate_requested": multi_product_rate,
        "actual_synthetic_multi_product_baskets": sum(
            len(item["product_keys"]) > 1 for item in baskets_data
        ),
        "seed": seed,
        "generation_method": (
            "Samples real SEVA basket templates with replacement; multi-product "
            "templates are intentionally oversampled to validate model behavior."
        ),
        "warning": (
            "Synthetic data is for software validation only. It does not represent "
            "real purchase frequencies and must not be reported as real-world model accuracy."
        ),
    }

    files = {
        "synthetic_customers.json": customers_data,
        "synthetic_products.json": products_data,
        "synthetic_purchase_baskets.json": baskets_data,
        "metadata.json": metadata,
    }
    for filename, payload in files.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )

    return metadata


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="crmapp/product_intelligence/tests/fixtures/synthetic_data")
    parser.add_argument("--customers", type=int, default=120)
    parser.add_argument("--baskets-per-customer", type=int, default=8)
    parser.add_argument("--multi-product-rate", type=float, default=0.75)
    parser.add_argument("--seed", type=int, default=20261025)
    args = parser.parse_args()

    result = generate_fixtures(
        output_dir=args.output_dir,
        customers=args.customers,
        baskets_per_customer=args.baskets_per_customer,
        multi_product_rate=args.multi_product_rate,
        seed=args.seed,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
