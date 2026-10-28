# SEVA ML Cross-Selling Validation Report

## Implementation
- Algorithm: FP-Growth with association rules
- Recommendation approach: ML-learned associations
- CRM scope: SEVA adapter; shared cross-selling code is designed for reuse

## Technical verification
- Python compileall: PASS
- Django system check: PASS
- Product Intelligence tests: 52/52 PASS
- Learned association rules on current records: 17

## Evaluation results

### Customer-level validation
- Train baskets: 7
- Test baskets: 1
- Evaluation queries: 2
- Precision@5: 0.00%
- Recall@5: 0.00%
- Independent customer validation: Yes
- Limitation: Very small held-out sample

### Basket-level diagnostic
- Train baskets: 6
- Test baskets: 2
- Evaluation queries: 6
- Successful hits: 2
- Precision@5: 6.67%
- Recall@5: 33.33%
- Returned-item precision: 28.57%
- Independent customer validation: No

## Interpretation
The ML pipeline and automated tests run successfully. Diagnostic hit inspection confirmed
two hits in service basket 33, for targets seva:1 and seva:32. The remaining four diagnostic
queries were misses.

These results do not establish reliable generalization. The current dataset has too few
multi-product baskets, and independent customer-level Recall@5 was zero on a very small
test sample. More genuine transaction data is required for stronger validation.

## Status
Technically functional; effectiveness validation remains preliminary.
Do not present diagnostic metrics as independent-customer performance.
