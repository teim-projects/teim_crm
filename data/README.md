# CRM ML Data Preparation – Audit Export

## Purpose
This package contains a first-pass, reproducible preparation of the supplied CRM SQL backup for a customer-to-product recommendation model covering Pest Control, Fumigation, and Product Sales.

## Important safeguards
- These files are derived from the supplied backup; they do not modify the source database.
- Existing customer IDs and product IDs are preserved.
- No customer names, phone numbers, email addresses, or full street addresses are exported.
- A quotation is an interest signal, not proof of purchase.
- Service approval, technician worklist completion, AMC allocation, and invoice evidence remain distinct event types.
- Invoice items are placed in a manual mapping review file. They are not automatically labelled as purchases.
- Duplicate-looking product names are flagged for review; product IDs are never merged automatically.
- Lead-to-customer matches are preliminary. Ambiguous and unmatched leads are explicitly marked.
- No synthetic data has been created or mixed into real CRM data.

## Files
- `customers_features.csv`: customer-level aggregate features and non-sensitive business attributes.
- `products_cleaned.csv`: product catalogue with category normalisation and source category retained.
- `interactions_real.csv`: event-level customer-product interactions with source table, source record ID, status, and proposed initial confidence weight.
- `lead_category_interest.csv`: lead-level category interest kept separate from product-level interactions.
- `lead_customer_identity_review.csv`: preliminary lead/customer matching outcomes.
- `product_mapping_review.csv`: repeated normalised product names requiring human review.
- `invoice_product_mapping_review.csv`: invoice line items and candidate catalogue matches for manual validation.
- `audit_summary.csv`: key record counts.

## Category normalisation
The catalogue categories are normalised to exactly:
- Pest Control
- Fumigation
- Product Sales

The original catalogue category is retained in `source_category`. Lead categories that cannot be confidently mapped are marked `Needs Review`.

## Initial interaction weights (provisional)
- Completed technician worklist linked to service-product: 4.0
- Approved service-product: 3.0
- Latest quotation-product link: 1.5
- AMC product-linked visit: 1.0
- Non-approved service-product: 0.75

These are starting experimental weights, not probabilities and not proof of purchase. Review them after checking the business workflow and evaluating model performance.

## Before training
1. Review `lead_customer_identity_review.csv` and resolve ambiguous matches only with business confirmation.
2. Review `product_mapping_review.csv`; preserve original product IDs.
3. Manually validate invoice line-to-product mappings in `invoice_product_mapping_review.csv`.
4. Confirm whether completed technician worklists reliably represent delivered work in the business process.
5. Build a time-based train/validation/test split using real historical event dates. Do not use synthetic records in the final test set.
6. Do not treat unobserved customer-product pairs as confirmed negatives.
7. Compare the model against simple popularity and category-based baselines before adopting a complex model.

## Known limitations
- Some event dates are absent in the source data.
- Product-sale purchase labels are sparse and invoice product mappings are uncertain.
- Lead category values are inconsistent and some cannot be mapped to a catalogue category.
- Customer identity matches based on contact/email are preliminary.
- This is a first-pass dataset preparation, not a final production training dataset.

## Identity matching note
The exported identity review uses a conservative sequential matching pass: primary contact, secondary contact, other contact, then customer email and other email. If the first populated matching field points to multiple CRM customers, the lead is marked ambiguous rather than forcing a later-field match. These are provisional links and require business review. The export's audit summary contains the counts from this exact reproducible pass.
