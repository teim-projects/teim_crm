
import unittest

from crmapp.product_intelligence.recommendations.output import (
    ProductRecommendationOutput,
)


class TestProductRecommendationOutput(unittest.TestCase):

    def setUp(self):
        self.formatter = ProductRecommendationOutput()

    def test_duplicate_product_keeps_highest_priority_type(self):
        recommendations = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "product_key": "seva:1",
                "product_name": "Cockroach Management",
                "candidate_type": "QUOTATION",
                "score": 25,
            },
            {
                "product_id": 1,
                "source_crm": "seva",
                "product_key": "seva:1",
                "product_name": "Cockroach Management",
                "candidate_type": "REPEAT",
                "score": 50,
            },
        ]

        result = self.formatter.format_recommendations(
            customer_id=35,
            recommendations=recommendations,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["product_key"], "seva:1")
        self.assertEqual(result[0]["recommendation_type"], "REPEAT")
        self.assertEqual(result[0]["score"], 50)

    def test_same_numeric_product_id_from_different_crms_stays_distinct(self):
        recommendations = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "product_key": "seva:1",
                "product_name": "Cockroach Management",
                "candidate_type": "REPEAT",
                "score": 50,
            },
            {
                "product_id": 1,
                "source_crm": "krishna",
                "product_key": "krishna:1",
                "product_name": "Cockroach Management",
                "candidate_type": "REPEAT",
                "score": 40,
            },
        ]

        result = self.formatter.format_recommendations(
            customer_id=35,
            recommendations=recommendations,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {item["product_key"] for item in result},
            {"seva:1", "krishna:1"},
        )

    def test_different_product_ids_with_same_name_stay_distinct(self):
        recommendations = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "product_key": "seva:1",
                "product_name": "Cockroach Management",
                "candidate_type": "REPEAT",
                "score": 50,
            },
            {
                "product_id": 54,
                "source_crm": "seva",
                "product_key": "seva:54",
                "product_name": "Cockroach Management",
                "candidate_type": "QUOTATION",
                "score": 25,
            },
        ]

        result = self.formatter.format_recommendations(
            customer_id=35,
            recommendations=recommendations,
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(
            {item["product_key"] for item in result},
            {"seva:1", "seva:54"},
        )

    def test_duplicate_entries_keep_higher_score_at_same_priority(self):
        recommendations = [
            {
                "product_id": 2,
                "source_crm": "seva",
                "product_key": "seva:2",
                "product_name": "Bed Bugs Management",
                "candidate_type": "REPEAT",
                "score": 20,
            },
            {
                "product_id": 2,
                "source_crm": "seva",
                "product_key": "seva:2",
                "product_name": "Bed Bugs Management",
                "candidate_type": "REPEAT",
                "score": 40,
            },
        ]

        result = self.formatter.format_recommendations(
            customer_id=35,
            recommendations=recommendations,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["score"], 40)

    def test_recommendation_type_is_supported_as_input(self):
        recommendations = [
            {
                "product_id": 3,
                "source_crm": "seva",
                "product_key": "seva:3",
                "product_name": "Example Product",
                "recommendation_type": "CROSS_SELL",
                "score": 35,
            }
        ]

        result = self.formatter.format_recommendations(
            customer_id=35,
            recommendations=recommendations,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["recommendation_type"],
            "CROSS_SELL",
        )


    def test_ml_association_metrics_are_preserved(self):
        recommendations = [
            {
                "product_id": 10,
                "source_crm": "seva",
                "product_key": "seva:10",
                "product_name": "Example Product",
                "candidate_type": "CROSS_SELL",
                "score": 45,
                "ml_support": 0.30,
                "ml_confidence": 0.75,
                "ml_lift": 1.80,
            }
        ]

        result = self.formatter.format_recommendations(
            customer_id=35,
            recommendations=recommendations,
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["ml_support"], 0.30)
        self.assertEqual(result[0]["ml_confidence"], 0.75)
        self.assertEqual(result[0]["ml_lift"], 1.80)



if __name__ == "__main__":
    unittest.main()
