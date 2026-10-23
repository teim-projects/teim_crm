
import unittest

from crmapp.product_intelligence.universal_features.customer_product_features import (
    UniversalCustomerProductFeatures,
)
from crmapp.product_intelligence.recommendations.candidate_generator import (
    ProductCandidateGenerator,
)
from crmapp.product_intelligence.recommendations.scoring_engine import (
    ProductScoringEngine,
)
from crmapp.product_intelligence.recommendations.output import (
    ProductRecommendationOutput,
)


class TestRecommendationFlow(unittest.TestCase):

    def setUp(self):
        self.customer_id = 10

        # Same numeric product ID exists in two different CRMs.
        self.quotation_products = [
            {
                "customer_id": self.customer_id,
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
                "quotation_id": 101,
            },
            {
                "customer_id": self.customer_id,
                "product_id": 1,
                "source_crm": "krishna",
                "source_product_id": "1",
                "product_key": "krishna:1",
                "quotation_id": 201,
            },
        ]

        self.feature_builder = UniversalCustomerProductFeatures()
        self.candidate_generator = ProductCandidateGenerator()
        self.scoring_engine = ProductScoringEngine()

    def test_customer_features_are_isolated_by_crm(self):
        seva_features = self.feature_builder.build_customer_features(
            customer_id=self.customer_id,
            service_products=[],
            quotation_products=self.quotation_products,
            amc_products=[],
            source_crm="seva",
        )

        krishna_features = self.feature_builder.build_customer_features(
            customer_id=self.customer_id,
            service_products=[],
            quotation_products=self.quotation_products,
            amc_products=[],
            source_crm="krishna",
        )

        self.assertEqual(
            {item["product_key"] for item in seva_features},
            {"seva:1"},
        )
        self.assertEqual(
            {item["product_key"] for item in krishna_features},
            {"krishna:1"},
        )

    def test_candidates_are_isolated_by_crm(self):
        seva_candidates = self.candidate_generator.generate(
            customer_id=self.customer_id,
            service_products=[],
            quotation_products=self.quotation_products,
            amc_products=[],
            source_crm="seva",
        )

        krishna_candidates = self.candidate_generator.generate(
            customer_id=self.customer_id,
            service_products=[],
            quotation_products=self.quotation_products,
            amc_products=[],
            source_crm="krishna",
        )

        self.assertEqual(
            {item["product_key"] for item in seva_candidates},
            {"seva:1"},
        )
        self.assertEqual(
            {item["product_key"] for item in krishna_candidates},
            {"krishna:1"},
        )
        self.assertTrue(
            all(
                item["candidate_type"] == "QUOTATION"
                for item in seva_candidates + krishna_candidates
            )
        )

    def test_same_numeric_product_id_stays_distinct_across_crms(self):
        output_formatter = ProductRecommendationOutput()
        all_output_keys = set()

        for source_crm, expected_key in (
            ("seva", "seva:1"),
            ("krishna", "krishna:1"),
        ):
            customer_features = (
                self.feature_builder.build_customer_features(
                    customer_id=self.customer_id,
                    service_products=[],
                    quotation_products=self.quotation_products,
                    amc_products=[],
                    source_crm=source_crm,
                )
            )

            candidates = self.candidate_generator.generate(
                customer_id=self.customer_id,
                service_products=[],
                quotation_products=self.quotation_products,
                amc_products=[],
                source_crm=source_crm,
            )

            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["product_key"], expected_key)

            scored_candidates = self.scoring_engine.score_candidates(
                candidates=candidates,
                customer_features=customer_features,
            )

            self.assertEqual(len(scored_candidates), 1)
            self.assertGreater(scored_candidates[0]["score"], 0)

            recommendations = output_formatter.format_recommendations(
                customer_id=self.customer_id,
                recommendations=scored_candidates,
            )

            self.assertEqual(len(recommendations), 1)
            self.assertEqual(
                recommendations[0]["recommendation_type"],
                "QUOTATION",
            )

            all_output_keys.update(
                item["product_key"] for item in recommendations
            )

        self.assertEqual(
            all_output_keys,
            {"seva:1", "krishna:1"},
        )

    def test_configured_cross_sell_can_use_catalogue_only_product(self):
        service_products = [
            {
                "customer_id": self.customer_id,
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
                "service_id": 101,
                "quantity": 1,
            }
        ]

        catalogue = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
                "product_name": "Existing service",
            },
            {
                "product_id": 2,
                "source_crm": "seva",
                "source_product_id": "2",
                "product_key": "seva:2",
                "product_name": "Configured complementary product",
            },
        ]

        relationships = [
            {
                "source_product_key": "seva:1",
                "target_product_key": "seva:2",
                "strength": 80,
                "reason": "Test-only configured relationship",
            }
        ]

        candidates = self.candidate_generator.generate(
            customer_id=self.customer_id,
            service_products=service_products,
            quotation_products=[],
            amc_products=[],
            source_crm="seva",
            product_catalog=catalogue,
            configured_relationships=relationships,
        )

        cross_sells = [
            item for item in candidates
            if item["candidate_type"] == "CROSS_SELL"
        ]

        self.assertEqual(len(cross_sells), 1)
        self.assertEqual(cross_sells[0]["product_key"], "seva:2")
        self.assertEqual(
            cross_sells[0]["relationship_source"], "configured"
        )
        self.assertEqual(
            cross_sells[0]["relationship_strength"], 80
        )
        self.assertEqual(
            cross_sells[0]["relationship_reason"],
            "Test-only configured relationship",
        )

    def test_configured_relationship_strength_affects_cross_sell_score(self):
        candidate = {
            "product_id": 2,
            "source_crm": "seva",
            "source_product_id": "2",
            "product_key": "seva:2",
            "candidate_type": "CROSS_SELL",
            "source_products": ["seva:1"],
            "co_occurrence_count": 0,
            "relationship_source": "configured",
            "relationship_strength": 80,
            "relationship_reason": "Test-only configured relationship",
        }

        result = self.scoring_engine.score_candidate(
            candidate=candidate,
            customer_features=[],
        )

        self.assertEqual(result["score"], 29)
        self.assertIn(
            "Test-only configured relationship",
            result["reasons"],
        )
        self.assertIn(
            "Configured relationship strength: 80/100",
            result["reasons"],
        )

    def test_ml_confidence_and_lift_affect_cross_sell_score(self):
        candidate = {
            "product_id": 2,
            "source_crm": "seva",
            "source_product_id": "2",
            "product_key": "seva:2",
            "candidate_type": "CROSS_SELL",
            "source_products": ["seva:1"],
            "co_occurrence_count": 0,
            "relationship_source": "ML_ASSOCIATION",
            "ml_support": 0.30,
            "ml_confidence": 0.75,
            "ml_lift": 1.80,
        }

        result = self.scoring_engine.score_candidate(
            candidate=candidate,
            customer_features=[],
        )

        self.assertEqual(result["score"], 24)
        self.assertIn(
            "ML association confidence: 75.0%",
            result["reasons"],
        )
        self.assertIn(
            "ML association lift: 1.80",
            result["reasons"],
        )

    # Historical cross-selling requires sufficient support.

    def test_single_historical_occurrence_is_filtered(self):
        services = [
            {
                "customer_id": 10,
                "service_id": 101,
                "product_id": 1,
                "source_crm": "seva",
            },
            {
                "customer_id": 20,
                "service_id": 201,
                "product_id": 1,
                "source_crm": "seva",
            },
            {
                "customer_id": 20,
                "service_id": 201,
                "product_id": 2,
                "source_crm": "seva",
            },
        ]

        catalogue = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
            },
            {
                "product_id": 2,
                "source_crm": "seva",
                "source_product_id": "2",
                "product_key": "seva:2",
            },
        ]

        candidates = self.candidate_generator.generate(
            customer_id=10,
            service_products=services,
            source_crm="seva",
            product_catalog=catalogue,
        )

        cross_sells = [
            item for item in candidates
            if item["candidate_type"] == "CROSS_SELL"
            and item["product_key"] == "seva:2"
        ]

        self.assertEqual(cross_sells, [])

    def test_two_historical_occurrences_generate_cross_sell(self):
        services = [
            {
                "customer_id": 10,
                "service_id": 101,
                "product_id": 1,
                "source_crm": "seva",
            },
            {
                "customer_id": 20,
                "service_id": 201,
                "product_id": 1,
                "source_crm": "seva",
            },
            {
                "customer_id": 20,
                "service_id": 201,
                "product_id": 2,
                "source_crm": "seva",
            },
            {
                "customer_id": 30,
                "service_id": 301,
                "product_id": 1,
                "source_crm": "seva",
            },
            {
                "customer_id": 30,
                "service_id": 301,
                "product_id": 2,
                "source_crm": "seva",
            },
        ]

        catalogue = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
            },
            {
                "product_id": 2,
                "source_crm": "seva",
                "source_product_id": "2",
                "product_key": "seva:2",
            },
        ]

        candidates = self.candidate_generator.generate(
            customer_id=10,
            service_products=services,
            source_crm="seva",
            product_catalog=catalogue,
        )

        cross_sells = [
            item for item in candidates
            if item["candidate_type"] == "CROSS_SELL"
            and item["product_key"] == "seva:2"
        ]

        self.assertEqual(len(cross_sells), 1)
        self.assertEqual(
            cross_sells[0]["co_occurrence_count"], 2
        )

    def test_configured_relationship_bypasses_historical_threshold(self):
        generator = ProductCandidateGenerator(
            min_historical_support=2
        )

        services = [
            {
                "customer_id": 10,
                "service_id": 101,
                "product_id": 1,
                "source_crm": "seva",
            },
        ]

        catalogue = [
            {
                "product_id": 1,
                "source_crm": "seva",
                "source_product_id": "1",
                "product_key": "seva:1",
            },
            {
                "product_id": 2,
                "source_crm": "seva",
                "source_product_id": "2",
                "product_key": "seva:2",
            },
        ]

        candidates = generator.generate(
            customer_id=10,
            service_products=services,
            source_crm="seva",
            product_catalog=catalogue,
            configured_relationships=[
                {
                    "source_product_key": "seva:1",
                    "target_product_key": "seva:2",
                    "strength": 80,
                    "reason": "Verified complementary relationship",
                }
            ],
        )

        cross_sells = [
            item for item in candidates
            if item["candidate_type"] == "CROSS_SELL"
            and item["product_key"] == "seva:2"
        ]

        self.assertEqual(len(cross_sells), 1)
        self.assertEqual(
            cross_sells[0]["relationship_source"], "configured"
        )
        self.assertEqual(
            cross_sells[0]["relationship_strength"], 80
        )


