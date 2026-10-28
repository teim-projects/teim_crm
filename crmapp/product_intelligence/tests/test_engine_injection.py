
import unittest

from crmapp.product_intelligence.recommendations.recommendation_engine import (
    ProductRecommendationEngine,
)


class TestRecommendationEngineInjection(unittest.TestCase):

    def setUp(self):
        self.product_adapter = object()
        self.service_adapter = object()
        self.quotation_adapter = object()
        self.amc_adapter = object()

    def create_engine(self, **kwargs):
        return ProductRecommendationEngine(
            source_crm="test_crm",
            product_adapter=self.product_adapter,
            service_adapter=self.service_adapter,
            quotation_adapter=self.quotation_adapter,
            amc_adapter=self.amc_adapter,
            **kwargs,
        )

    def test_engine_accepts_injected_adapters(self):
        engine = self.create_engine()

        self.assertIs(engine.product_adapter, self.product_adapter)
        self.assertIs(engine.service_adapter, self.service_adapter)
        self.assertIs(engine.quotation_adapter, self.quotation_adapter)
        self.assertIs(engine.amc_adapter, self.amc_adapter)

    def test_engine_uses_injected_crm_configuration(self):
        relationships = [
            {
                "source_product_key": "test_crm:1",
                "target_product_key": "test_crm:2",
                "strength": 70,
                "reason": "Test relationship",
            }
        ]

        engine = self.create_engine(
            product_relationships=relationships,
        )

        self.assertEqual(engine.source_crm, "test_crm")
        self.assertEqual(engine.product_relationships, relationships)

    def test_engine_does_not_load_default_crm_relationships(self):
        engine = self.create_engine()

        self.assertEqual(engine.product_relationships, [])

    def test_engine_requires_all_adapters(self):
        with self.assertRaises(ValueError):
            ProductRecommendationEngine(
                source_crm="test_crm",
                product_adapter=None,
                service_adapter=self.service_adapter,
                quotation_adapter=self.quotation_adapter,
                amc_adapter=self.amc_adapter,
            )


    def test_engine_instances_keep_different_crm_configurations_isolated(self):
        first_relationships = [
            {
                "source_product_key": "crm_a:1",
                "target_product_key": "crm_a:2",
                "strength": 70,
                "reason": "CRM A relationship",
            }
        ]
        second_relationships = [
            {
                "source_product_key": "crm_b:10",
                "target_product_key": "crm_b:20",
                "strength": 90,
                "reason": "CRM B relationship",
            }
        ]

        first_engine = ProductRecommendationEngine(
            source_crm="crm_a",
            product_adapter=object(),
            service_adapter=object(),
            quotation_adapter=object(),
            amc_adapter=object(),
            product_relationships=first_relationships,
        )
        second_engine = ProductRecommendationEngine(
            source_crm="crm_b",
            product_adapter=object(),
            service_adapter=object(),
            quotation_adapter=object(),
            amc_adapter=object(),
            product_relationships=second_relationships,
        )

        self.assertEqual(first_engine.source_crm, "crm_a")
        self.assertEqual(second_engine.source_crm, "crm_b")
        self.assertEqual(first_engine.product_relationships, first_relationships)
        self.assertEqual(second_engine.product_relationships, second_relationships)
        self.assertIsNot(
            first_engine.product_relationships,
            second_engine.product_relationships,
        )


if __name__ == "__main__":
    unittest.main()
