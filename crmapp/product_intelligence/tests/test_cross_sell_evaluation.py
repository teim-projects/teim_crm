import unittest

from crmapp.product_intelligence.cross_selling.cross_sell_evaluation import (
    evaluate_cross_sell_model,
    evaluate_cross_sell_model_by_basket,
)


def make_records():
    """Use a fictional CRM to verify CRM-independent evaluation."""
    baskets = [
        ("c1", "s1", ["A", "B"]),
        ("c2", "s2", ["A", "B"]),
        ("c3", "s3", ["A", "C"]),
        ("c4", "s4", ["A", "C"]),
    ]
    records = []
    for customer, service, products in baskets:
        for product in products:
            records.append({
                "source_crm": "testcrm",
                "customer_id": customer,
                "service_id": service,
                "product_id": product,
                "source_product_id": product,
            })
    return records


class CrossSellEvaluationTests(unittest.TestCase):

    def test_training_does_not_merge_separate_transactions_for_one_customer(self):
        from crmapp.product_intelligence.cross_selling.cross_sell_ml import CrossSellMLEngine

        records = [
            {"source_crm": "crm_a", "customer_id": 1, "service_id": 101, "product_id": 10, "product_key": "crm_a:10"},
            {"source_crm": "crm_a", "customer_id": 1, "service_id": 102, "product_id": 20, "product_key": "crm_a:20"},
            {"source_crm": "crm_a", "customer_id": 2, "service_id": 103, "product_id": 10, "product_key": "crm_a:10"},
            {"source_crm": "crm_a", "customer_id": 3, "service_id": 104, "product_id": 20, "product_key": "crm_a:20"},
        ]

        model = CrossSellMLEngine(
            min_support=0.1,
            min_confidence=0.1,
            min_lift=0.0,
        ).fit(records, source_crm="crm_a")

        self.assertTrue(
            model.rules_.empty,
            "Separate transactions must not create a product association.",
        )

    def test_training_excludes_records_from_other_crms(self):
        from crmapp.product_intelligence.cross_selling.cross_sell_ml import (
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
        result = evaluate_cross_sell_model(
            make_records(), test_size=0.5, random_state=42, k=2
        )

        self.assertEqual(result["algorithm"], "FP-Growth Association Rules")
        self.assertEqual(result["evaluation_mode"], "customer_level")
        self.assertTrue(result["independent_customer_validation"])
        self.assertEqual(result["warning"], "Small held-out sample: interpret metrics cautiously.")
        self.assertEqual(result["train_baskets"], 2)
        self.assertEqual(result["test_baskets"], 2)
        self.assertGreater(result["evaluation_queries"], 0)

        for metric in (
            "precision_at_2",
            "recall_at_2",
            "hit_rate_at_2",
            "f1_at_2",
        ):
            self.assertGreaterEqual(result[metric], 0.0)
            self.assertLessEqual(result[metric], 1.0)

    def test_basket_diagnostic_is_explicitly_labelled(self):
        result = evaluate_cross_sell_model_by_basket(
            make_records(), test_size=0.5, random_state=42, k=2
        )

        self.assertEqual(
            result["evaluation_mode"], "basket_level_diagnostic"
        )
        self.assertFalse(result["independent_customer_validation"])
        self.assertIn("Diagnostic only", result["warning"])
        self.assertEqual(result["train_baskets"], 2)
        self.assertEqual(result["test_baskets"], 2)
        self.assertGreater(result["evaluation_queries"], 0)

    def test_evaluation_rejects_insufficient_multi_product_baskets(self):
        records = [
            {
                "source_crm": "testcrm",
                "customer_id": "c1",
                "service_id": "s1",
                "product_id": "A",
            },
            {
                "source_crm": "testcrm",
                "customer_id": "c2",
                "service_id": "s2",
                "product_id": "B",
            },
        ]

        with self.assertRaisesRegex(ValueError, "multi-product"):
            evaluate_cross_sell_model(records)

        with self.assertRaisesRegex(ValueError, "multi-product"):
            evaluate_cross_sell_model_by_basket(records)


    def test_evaluator_does_not_inject_seva_as_default_crm(self):
        records = make_records()
        for record in records:
            record.pop("source_crm", None)

        result = evaluate_cross_sell_model(
            records, test_size=0.5, random_state=42, k=2
        )

        self.assertEqual(result["evaluation_mode"], "customer_level")
        self.assertTrue(result["independent_customer_validation"])


    def test_personalized_recommendations_exclude_owned_products(self):
        import pandas as pd
        from crmapp.product_intelligence.cross_selling.cross_sell_ml import (
            CrossSellMLEngine,
        )

        model = CrossSellMLEngine()
        model.rules_ = pd.DataFrame([
            {
                "antecedents": frozenset({"seva:1"}),
                "consequents": frozenset({"seva:2"}),
                "support": 0.4, "confidence": 0.8, "lift": 1.5,
            },
            {
                "antecedents": frozenset({"seva:1"}),
                "consequents": frozenset({"seva:3"}),
                "support": 0.3, "confidence": 0.7, "lift": 1.3,
            },
        ])

        results = model.recommend({"seva:1", "seva:2"})

        keys = {item["product_key"] for item in results}
        self.assertNotIn("seva:1", keys)
        self.assertNotIn("seva:2", keys)
        self.assertIn("seva:3", keys)

    def test_general_recommendations_are_not_supported(self):
        from crmapp.product_intelligence.cross_selling.cross_sell_ml import (
            CrossSellMLEngine,
        )
        self.assertFalse(hasattr(CrossSellMLEngine, "recommend_general"))


class CrossSellMLEngineCoreTests(unittest.TestCase):
    """Core FP-Growth engine tests using deterministic synthetic transactions."""

    def make_records(self):
        records = []
        baskets = (
            [["A", "B"]] * 3
            + [["A", "C"]] * 2
            + [["D", "E"]] * 2
        )
        for index, products in enumerate(baskets):
            for product in products:
                records.append({
                    "source_crm": "testcrm",
                    "customer_id": f"customer_{index}",
                    "service_id": f"service_{index}",
                    "product_id": product,
                    "source_product_id": product,
                })
        return records

    def make_model(self):
        from crmapp.product_intelligence.cross_selling.cross_sell_ml import (
            CrossSellMLEngine,
        )
        return CrossSellMLEngine(
            min_support=0.1, min_confidence=0.1, min_lift=0.0
        )

    def test_fit_learns_real_association_rules(self):
        model = self.make_model().fit(self.make_records())
        self.assertFalse(model.rules_.empty)
        pairs = {
            (next(iter(row.antecedents)), next(iter(row.consequents)))
            for row in model.rules_.itertuples()
        }
        self.assertIn(("testcrm:A", "testcrm:B"), pairs)

    def test_recommendation_returns_unowned_product_and_metrics(self):
        model = self.make_model().fit(self.make_records())
        results = model.recommend(["testcrm:A"], limit=5)
        by_key = {item["product_key"]: item for item in results}

        self.assertIn("testcrm:B", by_key)
        self.assertNotIn("testcrm:A", by_key)
        item = by_key["testcrm:B"]
        self.assertTrue(0 <= item["support"] <= 1)
        self.assertTrue(0 <= item["confidence"] <= 1)
        self.assertGreaterEqual(item["lift"], 0)
        self.assertIn("testcrm:A", item["source_products"])

    def test_recommendation_limit_and_empty_model(self):
        self.assertEqual(self.make_model().recommend(["testcrm:A"]), [])
        model = self.make_model().fit(self.make_records())
        self.assertLessEqual(
            len(model.recommend(["testcrm:A"], limit=1)), 1
        )
        self.assertEqual(model.recommend(["testcrm:A"], limit=0), [])

    def test_model_does_not_learn_cross_crm_associations(self):
        records = [
            {"source_crm": "crm_a", "service_id": "1", "product_id": "A"},
            {"source_crm": "crm_a", "service_id": "2", "product_id": "B"},
            {"source_crm": "crm_b", "service_id": "3", "product_id": "A"},
            {"source_crm": "crm_b", "service_id": "3", "product_id": "B"},
        ]
        model = self.make_model().fit(records, source_crm="crm_a")
        self.assertTrue(model.rules_.empty)

