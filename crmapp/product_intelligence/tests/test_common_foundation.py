
import unittest

from crmapp.product_intelligence.bucketing import ProductBucketer
from crmapp.product_intelligence.universal_features.customer_product_features import (
    UniversalCustomerProductFeatures,
)
from crmapp.product_intelligence.recommendations.candidate_generator import (
    ProductCandidateGenerator,
)


class TestProductBucketer(unittest.TestCase):

    def test_product_uses_configured_bucket(self):
        class TestRules:
            @staticmethod
            def get_bucket(product):
                if product.get("category") == "Pest Control":
                    return "PEST_CONTROL"
                return None

        bucketer = ProductBucketer(rule_provider=TestRules)

        products = [
            {
                "product_id": 1,
                "product_name": "Cockroach Management",
                "category": "Pest Control",
            }
        ]

        result = bucketer.bucket_products(products)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bucket"], "PEST_CONTROL")

    def test_unknown_product_uses_category(self):
        class TestRules:
            @staticmethod
            def get_bucket(product):
                return None

        bucketer = ProductBucketer(rule_provider=TestRules)

        products = [
            {
                "product_id": 2,
                "product_name": "Unknown Product",
                "category": "Fumigation",
            }
        ]

        result = bucketer.bucket_products(products)

        self.assertEqual(len(result), 1)
        self.assertIsNone(result[0]["bucket"])


class TestUniversalCustomerProductFeatures(unittest.TestCase):

    def test_customer_features_include_service_and_quotation_history(self):
        builder = UniversalCustomerProductFeatures()

        service_products = [
            {
                "customer_id": 10,
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
                "service_id": 101,
                "quantity": 2,
            }
        ]

        quotation_products = [
            {
                "customer_id": 10,
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
                "quotation_id": 201,
            }
        ]

        features = builder.build_customer_features(
            customer_id=10,
            service_products=service_products,
            quotation_products=quotation_products,
            amc_products=[],
            source_crm="seva",
        )

        self.assertEqual(len(features), 1)
        self.assertEqual(features[0]["product_key"], "seva:1")
        self.assertEqual(features[0]["service_count"], 1)
        self.assertEqual(features[0]["quotation_count"], 1)


class TestProductCandidateGenerator(unittest.TestCase):

    def test_quotation_only_product_is_not_repeat(self):
        generator = ProductCandidateGenerator()

        candidates = generator.generate(
            customer_id=10,
            source_crm="seva",
            service_products=[],
            quotation_products=[
                {
                    "customer_id": 10,
                    "product_id": 1,
                    "source_crm": "seva",
                    "source_product_id": "1",
                    "product_key": "seva:1",
                    "quotation_id": 101,
                }
            ],
            amc_products=[],
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["product_key"], "seva:1")
        self.assertEqual(candidates[0]["candidate_type"], "QUOTATION")
        self.assertEqual(candidates[0]["quotation_count"], 1)

    def test_quotation_count_uses_distinct_quotation_ids(self):
        generator = ProductCandidateGenerator()

        candidates = generator.generate(
            customer_id=10,
            source_crm="seva",
            service_products=[],
            quotation_products=[
                {
                    "customer_id": 10,
                    "product_id": 1,
                    "source_crm": "seva",
                    "source_product_id": "1",
                    "product_key": "seva:1",
                    "quotation_id": 101,
                },
                {
                    "customer_id": 10,
                    "product_id": 1,
                    "source_crm": "seva",
                    "source_product_id": "1",
                    "product_key": "seva:1",
                    "quotation_id": 101,
                },
                {
                    "customer_id": 10,
                    "product_id": 1,
                    "source_crm": "seva",
                    "source_product_id": "1",
                    "product_key": "seva:1",
                    "quotation_id": 102,
                },
            ],
            amc_products=[],
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["quotation_count"], 2)


if __name__ == "__main__":
    unittest.main()

