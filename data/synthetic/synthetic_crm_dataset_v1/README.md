# Synthetic CRM Recommendation Dataset v1

## Purpose
This dataset contains 5,000 rule-based synthetic product-interest scenarios for experimentation and model-development support.

## Important boundaries
- All synthetic customers use IDs beginning with `SYN_CUST_`.
- All rows have `data_source=synthetic`.
- No real CRM customer IDs are used.
- No real purchase or service-delivery records are created.
- `scenario_label=synthetic_product_interest` and `intent_label=potential_interest` describe simulated interest only.
- These rows must never be displayed as actual customer purchase/service history.
- Do not use synthetic rows in the final real-world validation or test evaluation.
- The product IDs are taken from the existing CRM product catalogue. Original product categories and IDs are not modified.
- Only products marked `recommendation_eligible=Yes` and passing the category/group consistency filter were sampled.
- Product classifications are AI-assisted provisional suggestions, not business-approved product truth.

## Generation assumptions
- Category allocation: Pest Control 2,000; Product Sales 2,000; Fumigation 1,000.
- 1,000 synthetic customer IDs are used.
- Customer segment and type distributions are scenario assumptions inspired by broad CRM lead-segment patterns, not verified unique-customer demographics.
- Category-specific segment distributions are heuristic assumptions to create plausible scenarios, not measured customer-product purchase relationships.
- Product selection is balanced across eligible recommendation groups within each category.
- Fixed random seed: 20261104.

## Recommended use
1. Train a real-data-only baseline first.
2. Train a separate experimental model using real training data plus synthetic training scenarios.
3. Keep synthetic validation/test rows separate from the real validation/test datasets.
4. Compare both models on untouched real validation/test data.
5. If synthetic augmentation does not improve real-data metrics, do not use it.
6. Keep real customer purchase/service history sourced only from the original CRM records.

## Not suitable for
- Reporting actual sales, purchases, completed services, customer conversion, or revenue.
- Claiming model accuracy based on synthetic validation/test splits.
- Replacing the original CRM catalogue or interaction history.
