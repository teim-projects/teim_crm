from pathlib import Path
import shutil

root = Path("crmapp/product_intelligence/recommendations")
ml_file = root / "cross_sell_ml.py"
engine_file = root / "recommendation_engine.py"
score_file = root / "scoring_engine.py"

files = [ml_file, engine_file, score_file]
original = {p: p.read_text(encoding="utf-8-sig") for p in files}

# Fail safely before writing anything if the expected code differs.
ml_old = '''        customer_id = record.get("customer_id")
        crm = str(record.get("source_crm") or "seva").strip().lower()

        if customer_id is None:
            return None

        return crm, str(customer_id).strip()'''

ml_new = '''        crm = str(record.get("source_crm") or "seva").strip().lower()

        # Prefer the actual service/transaction basket when available.
        service_id = record.get("service_id")
        if service_id is not None:
            return crm, "service", str(service_id).strip()

        transaction_id = record.get("transaction_id")
        if transaction_id is not None:
            return crm, "transaction", str(transaction_id).strip()

        customer_id = record.get("customer_id")
        if customer_id is None:
            return None

        return crm, "customer", str(customer_id).strip()'''

engine_anchor = '''        eligible_candidates = []

        for candidate in candidates:'''

engine_insert = '''        # Learn associations from CRM-normalized purchase history.
        self.cross_sell_ml_engine.fit(service_products)

        customer_service_records = [
            r for r in service_products
            if self.candidate_generator._belongs_to_customer(
                r, customer_id, self.source_crm
            )
        ]
        purchased_keys = {
            self._product_key(r)
            for r in customer_service_records
            if self._product_key(r) is not None
        }

        ml_predictions = self.cross_sell_ml_engine.recommend(purchased_keys)

        # Never recommend products already used, quoted, or covered by AMC.
        excluded_keys = set()
        for records in (
            service_products, quotation_products, amc_products
        ):
            for record in records:
                if self.candidate_generator._belongs_to_customer(
                    record, customer_id, self.source_crm
                ):
                    key = self._product_key(record)
                    if key is not None:
                        excluded_keys.add(key)

        candidate_by_key = {
            self._product_key(c): c
            for c in candidates
            if self._product_key(c) is not None
        }

        for prediction in ml_predictions:
            target_key = prediction["product_key"]
            if target_key in excluded_keys or target_key not in product_map:
                continue

            existing = candidate_by_key.get(target_key)
            if existing is not None:
                if existing.get("candidate_type") != "CROSS_SELL":
                    continue
                # Enrich an existing cross-sell rather than duplicating it.
                existing["ml_support"] = prediction["support"]
                existing["ml_confidence"] = prediction["confidence"]
                existing["ml_lift"] = prediction["lift"]
                existing["relationship_source"] = "ML_ASSOCIATION"
                continue

            product = product_map[target_key]
            candidate = {
                **product,
                "candidate_type": "CROSS_SELL",
                "service_count": 0,
                "total_quantity": 0,
                "amc_visit_count": 0,
                "amc_count": 0,
                "source_products": prediction["source_products"],
                "co_occurrence_count": 0,
                "quotation_interest": False,
                "relationship_source": "ML_ASSOCIATION",
                "relationship_strength": round(
                    prediction["confidence"] * 100
                ),
                "relationship_reason": (
                    "Learned product association: confidence "
                    f"{prediction['confidence']:.1%}, lift "
                    f"{prediction['lift']:.2f}"
                ),
                "ml_support": prediction["support"],
                "ml_confidence": prediction["confidence"],
                "ml_lift": prediction["lift"],
            }
            candidates.append(candidate)
            candidate_by_key[target_key] = candidate

        eligible_candidates = []

        for candidate in candidates:'''

score_anchor = '''            # Historical association evidence.'''

score_insert = '''            # Learned association evidence, when available.
            ml_confidence = candidate.get("ml_confidence")
            ml_lift = candidate.get("ml_lift")
            if ml_confidence is not None:
                score += min(20, round(float(ml_confidence) * 20))
                reasons.append(
                    f"ML association confidence: {float(ml_confidence):.1%}"
                )
            if ml_lift is not None:
                lift = float(ml_lift)
                score += min(10, max(0, round((lift - 1.0) * 5)))
                reasons.append(f"ML association lift: {lift:.2f}")

            # Historical association evidence.'''

if ml_old not in original[ml_file]:
    raise SystemExit("STOP: CrossSellMLEngine customer-key code did not match.")
if engine_anchor not in original[engine_file]:
    raise SystemExit("STOP: Recommendation pipeline insertion point did not match.")
if score_anchor not in original[score_file]:
    raise SystemExit("STOP: Cross-sell scoring insertion point did not match.")

updated = {
    ml_file: original[ml_file].replace(ml_old, ml_new, 1),
    engine_file: original[engine_file].replace(
        engine_anchor, engine_insert, 1
    ),
    score_file: original[score_file].replace(
        score_anchor, score_insert, 1
    ),
}

# Back up all three originals before writing any changes.
for path in files:
    shutil.copy2(path, path.with_suffix(path.suffix + ".pre_ml.bak"))

try:
    for path, content in updated.items():
        path.write_text(content, encoding="utf-8")
except Exception:
    for path, content in original.items():
        path.write_text(content, encoding="utf-8")
    raise

print("PATCH APPLIED: service-level ML training and recommendation integration.")
print("Backups saved with the .pre_ml.bak suffix.")
