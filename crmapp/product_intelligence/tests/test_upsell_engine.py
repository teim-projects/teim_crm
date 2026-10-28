
import unittest

from crmapp.product_intelligence.recommendations.upsell_engine import (
    ProductUpsellEngine,
)


class FakeUpgradeRules:
    """Test-only upgrade rules; no real CRM product IDs."""

    RULES = {
        "crm_a:basic": ["crm_a:premium"],
        "crm_b:standard": ["crm_b:advanced"],
    }

    @classmethod
    def get_upsell_products(cls, source_product_id):
        return cls.RULES.get(source_product_id, [])

    @classmethod
    def is_upsell(cls, source_product_id, candidate_product_id):
        if source_product_id == candidate_product_id:
            return False
        return candidate_product_id in cls.get_upsell_products(
            source_product_id
        )


class TestProductUpsellEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ProductUpsellEngine(FakeUpgradeRules)

    def test_verified_upgrade_is_recognized(self):
        self.assertTrue(
            self.engine.is_upsell("crm_a:basic", "crm_a:premium")
        )

    def test_same_product_is_not_an_upsell(self):
        self.assertFalse(
            self.engine.is_upsell("crm_a:basic", "crm_a:basic")
        )

    def test_complementary_or_unknown_product_is_not_an_upsell(self):
        self.assertFalse(
            self.engine.is_upsell("crm_a:basic", "crm_a:accessory")
        )

    def test_candidates_are_limited_to_available_products(self):
        candidates = self.engine.generate_candidates(
            source_product_ids=["crm_a:basic"],
            candidate_product_ids=[
                "crm_a:premium",
                "crm_a:accessory",
            ],
        )
        self.assertEqual(candidates, ["crm_a:premium"])

    def test_rules_are_isolated_by_crm_namespace(self):
        candidates = self.engine.generate_candidates(
            source_product_ids=["crm_a:basic"],
            candidate_product_ids=[
                "crm_a:premium",
                "crm_b:advanced",
            ],
        )
        self.assertEqual(candidates, ["crm_a:premium"])


if __name__ == "__main__":
    unittest.main()
