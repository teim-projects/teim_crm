from pathlib import Path

engine_path = Path("crmapp/product_intelligence/recommendations/cross_sell_ml.py")
test_path = Path("crmapp/product_intelligence/tests/test_cross_sell_evaluation.py")

engine = engine_path.read_text(encoding="utf-8-sig")
old_engine = '''        for record in purchase_records:
            if not isinstance(record, dict):
                continue

            basket = self._basket_key(record, selected_crm)
'''
new_engine = '''        for record in purchase_records:
            if not isinstance(record, dict):
                continue

            record_crm = str(record.get("source_crm") or "").strip().lower()
            if selected_crm and record_crm and record_crm != selected_crm:
                continue

            basket = self._basket_key(record, selected_crm)
'''

if engine.count(old_engine) != 1:
    raise SystemExit("STOP: Expected fit() code was not found exactly once.")

tests = test_path.read_text(encoding="utf-8-sig")
marker = '''    def test_customer_level_split_and_metrics(self):
'''
new_test = '''    def test_training_excludes_records_from_other_crms(self):
        from crmapp.product_intelligence.recommendations.cross_sell_ml import (
            CrossSellMLEngine,
        )

        records = [
            # Selected CRM: separate single-product transactions.
            {
                "source_crm": "crm_a", "customer_id": 1,
                "service_id": 101, "product_id": "A",
            },
            {
                "source_crm": "crm_a", "customer_id": 2,
                "service_id": 102, "product_id": "B",
            },
            # Other CRM: this co-purchase must not create a crm_a rule.
            {
                "source_crm": "crm_b", "customer_id": 3,
                "service_id": 201, "product_id": "A",
            },
            {
                "source_crm": "crm_b", "customer_id": 3,
                "service_id": 201, "product_id": "B",
            },
        ]

        model = CrossSellMLEngine(
            min_support=0.1,
            min_confidence=0.1,
            min_lift=0.0,
        ).fit(records, source_crm="crm_a")

        self.assertTrue(
            model.rules_.empty,
            "Records from another CRM must not create association rules.",
        )

    def test_customer_level_split_and_metrics(self):
'''

if tests.count(marker) != 1:
    raise SystemExit("STOP: Expected test insertion point was not found exactly once.")

engine_path.write_text(engine.replace(old_engine, new_engine, 1), encoding="utf-8")
test_path.write_text(tests.replace(marker, new_test, 1), encoding="utf-8")

print("PATCH APPLIED: CRM isolation filter and regression test added.")
