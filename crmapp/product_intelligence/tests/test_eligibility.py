import unittest

from crmapp.product_intelligence.recommendations.eligibility import (
    ProductEligibility,
)


class TestProductEligibility(unittest.TestCase):

    def setUp(self):
        self.eligibility = ProductEligibility()

    def test_normal_product_is_eligible(self):
        product = {
            "product_id": 34,
            "source_crm": "seva",
            "source_product_id": "34",
            "product_key": "seva:34",
            "product_name": "Rat Snap Trap",
        }

        self.assertTrue(self.eligibility.is_eligible(product))

    def test_configured_product_key_is_excluded(self):
        eligibility = ProductEligibility(
            excluded_product_keys=["seva:84"]
        )

        product = {
            "product_key": "seva:84",
            "product_name": "Transportation Charges",
        }

        self.assertFalse(eligibility.is_eligible(product))

    def test_same_numeric_id_from_another_crm_is_not_excluded(self):
        eligibility = ProductEligibility(
            excluded_product_keys=["seva:84"]
        )

        product = {
            "product_key": "krishna:84",
            "product_name": "Example Product",
        }

        self.assertTrue(eligibility.is_eligible(product))

    def test_configured_name_is_excluded_case_insensitively(self):
        eligibility = ProductEligibility(
            excluded_product_names=["Transportation Charges"]
        )

        product = {
            "product_key": "seva:84",
            "product_name": "transportation charges",
        }

        self.assertFalse(eligibility.is_eligible(product))

    def test_missing_product_identity_does_not_crash(self):
        product = {
            "product_name": "Example Product",
        }

        self.assertTrue(self.eligibility.is_eligible(product))

    def test_filter_products_preserves_only_eligible_products(self):
        eligibility = ProductEligibility(
            excluded_product_keys=["seva:84"]
        )

        products = [
            {"product_key": "seva:34", "product_name": "Rat Snap Trap"},
            {"product_key": "seva:84", "product_name": "Transportation Charges"},
        ]

        result = eligibility.filter_products(products)

        self.assertEqual(
            [product["product_key"] for product in result],
            ["seva:34"],
        )


if __name__ == "__main__":
    unittest.main()