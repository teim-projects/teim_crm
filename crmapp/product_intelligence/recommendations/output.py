
class ProductRecommendationOutput:
    """Format and deduplicate recommendations using CRM-aware product IDs."""

    RECOMMENDATION_PRIORITY = {
        "REPEAT": 4,
        "CROSS_SELL": 2,
        "QUOTATION": 1,
    }

    @staticmethod
    def _product_key(recommendation):
        existing_key = recommendation.get("product_key")

        if existing_key:
            return str(existing_key).strip().lower()

        source_crm = str(
            recommendation.get("source_crm") or ""
        ).strip().lower()

        source_product_id = recommendation.get(
            "source_product_id",
            recommendation.get("product_id"),
        )

        if source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()

        if not source_crm or not source_product_id:
            return None

        return f"{source_crm}:{source_product_id}"

    @classmethod
    def _deduplicate_recommendations(cls, recommendations):
        """Keep the strongest recommendation for each product."""

        best_by_product = {}

        for recommendation in recommendations:
            product_key = cls._product_key(recommendation)

            if product_key is None:
                continue

            candidate_type = str(
                recommendation.get("candidate_type")
                or recommendation.get("recommendation_type")
                or ""
            ).strip().upper()

            try:
                score = float(recommendation.get("score", 0) or 0)
            except (TypeError, ValueError):
                score = 0

            current = dict(recommendation)
            current["product_key"] = product_key
            current["_normalised_type"] = candidate_type
            current["_normalised_score"] = score

            existing = best_by_product.get(product_key)

            if existing is None:
                best_by_product[product_key] = current
                continue

            current_rank = (
                cls.RECOMMENDATION_PRIORITY.get(candidate_type, 0),
                score,
            )
            existing_rank = (
                cls.RECOMMENDATION_PRIORITY.get(
                    existing["_normalised_type"], 0
                ),
                existing["_normalised_score"],
            )

            if current_rank > existing_rank:
                best_by_product[product_key] = current

        deduplicated = list(best_by_product.values())

        for recommendation in deduplicated:
            recommendation.pop("_normalised_type", None)
            recommendation.pop("_normalised_score", None)

        return sorted(
            deduplicated,
            key=lambda recommendation: (
                -float(recommendation.get("score", 0) or 0),
                cls._product_key(recommendation) or "",
            ),
        )

    @classmethod
    def format_recommendation(cls, customer_id, recommendation):
        product_key = cls._product_key(recommendation)

        source_crm = str(
            recommendation.get("source_crm") or ""
        ).strip().lower()

        source_product_id = recommendation.get(
            "source_product_id",
            recommendation.get("product_id"),
        )

        recommendation_type = (
            recommendation.get("candidate_type")
            or recommendation.get("recommendation_type")
        )

        return {
            "customer_id": customer_id,
            "product_id": recommendation.get("product_id"),
            "source_crm": source_crm,
            "source_product_id": (
                str(source_product_id)
                if source_product_id is not None
                else None
            ),
            "product_key": product_key,
            "product_name": recommendation.get("product_name"),
            "category": recommendation.get("category"),

            # Preserve the type under both names for compatibility.
            "candidate_type": recommendation_type,
            "recommendation_type": recommendation_type,

            "score": recommendation.get("score", 0),
            "reasons": recommendation.get("reasons", []),

            # Preserve ML association evidence from the shared engine.
            "ml_support": recommendation.get("ml_support"),
            "ml_confidence": recommendation.get("ml_confidence"),
            "ml_lift": recommendation.get("ml_lift"),
            "source_products": recommendation.get(
                "source_products", []
            ),
            "co_occurrence_count": recommendation.get(
                "co_occurrence_count", 0
            ),
            "quotation_interest": recommendation.get(
                "quotation_interest", False
            ),

            # Preserve evidence explaining why the recommendation exists.
            "relationship_source": recommendation.get(
                "relationship_source"
            ),
            "relationship_strength": recommendation.get(
                "relationship_strength", 0
            ),
            "relationship_reason": recommendation.get(
                "relationship_reason"
            ),
            "upgrade_source_product_key": recommendation.get(
                "upgrade_source_product_key"
            ),
            "upgrade_reason": recommendation.get("upgrade_reason"),
        }

    @classmethod
    def format_recommendations(cls, customer_id, recommendations):
        deduplicated = cls._deduplicate_recommendations(
            recommendations
        )

        return [
            cls.format_recommendation(
                customer_id=customer_id,
                recommendation=recommendation,
            )
            for recommendation in deduplicated
        ]
