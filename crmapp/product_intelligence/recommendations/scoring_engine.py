class ProductScoringEngine:
    """CRM-independent product recommendation scoring engine."""

    @staticmethod
    def _key(record):
        if record.get("product_key"):
            return str(record["product_key"])

        product_id = record.get("product_id")
        source_crm = str(
            record.get("source_crm") or ""
        ).strip().lower()
        source_product_id = record.get(
            "source_product_id", product_id
        )

        if source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()
        if not source_product_id:
            return None

        return f"{source_crm}:{source_product_id}"

    def score_candidate(
        self,
        candidate,
        customer_features=None,
        association_metrics_engine=None,
        association_metrics=None,
    ):
        customer_features = customer_features or []

        product_key = self._key(candidate)
        candidate_type = candidate.get("candidate_type")

        feature_map = {
            self._key(feature): feature
            for feature in customer_features
            if self._key(feature) is not None
        }

        feature = feature_map.get(
            product_key,
            {
                "service_count": 0,
                "total_quantity": 0,
                "quotation_count": 0,
                "amc_visit_count": 0,
                "amc_count": 0,
            },
        )

        score = 0
        reasons = []

        if candidate_type == "REPEAT":
            service_count = feature.get("service_count", 0)
            amc_visit_count = feature.get("amc_visit_count", 0)
            quotation_count = feature.get("quotation_count", 0)

            if service_count >= 5:
                score += 40
                reasons.append(
                    f"Product used in {service_count} service records"
                )
            elif service_count >= 3:
                score += 30
                reasons.append(
                    f"Product used in {service_count} service records"
                )
            elif service_count >= 2:
                score += 20
                reasons.append(
                    f"Product used in {service_count} service records"
                )
            elif service_count == 1:
                score += 10
                reasons.append(
                    "Product previously used by the customer"
                )

            if amc_visit_count >= 25:
                score += 30
                reasons.append(
                    f"Product has {amc_visit_count} AMC visits"
                )
            elif amc_visit_count >= 10:
                score += 20
                reasons.append(
                    f"Product has {amc_visit_count} AMC visits"
                )
            elif amc_visit_count > 0:
                score += 10
                reasons.append(
                    f"Product has {amc_visit_count} AMC visits"
                )

            if quotation_count > 0:
                score += 10
                reasons.append(
                    f"Product appears in {quotation_count} quotation records"
                )

        elif candidate_type == "CROSS_SELL":
            co_occurrence_count = candidate.get(
                "co_occurrence_count", 0
            )
            source_products = candidate.get("source_products", [])
            quotation_count = feature.get("quotation_count", 0)

            if co_occurrence_count >= 3:
                score += 40
                reasons.append(
                    f"Observed together in {co_occurrence_count} services"
                )
            elif co_occurrence_count == 2:
                score += 30
                reasons.append(
                    f"Observed together in {co_occurrence_count} services"
                )
            elif co_occurrence_count == 1:
                score += 20
                reasons.append(
                    "Observed together in 1 service"
                )

            if len(source_products) >= 2:
                score += 15
                reasons.append(
                    "Supported by multiple products already used by the customer"
                )
            elif len(source_products) == 1:
                score += 5
                reasons.append(
                    "Supported by a product already used by the customer"
                )

            if quotation_count > 0:
                score += 10
                reasons.append(
                    f"Product appears in {quotation_count} quotation records"
                )

            # Learned association evidence, when available.
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

            # Historical association evidence.
            if (
                association_metrics_engine is not None
                and association_metrics is not None
            ):
                best_confidence = 0
                best_lift = 0
                best_pair_count = 0

                for source_product_key in source_products:
                    confidence = (
                        association_metrics_engine.get_confidence(
                            association_metrics,
                            source_product_key,
                            product_key,
                        )
                    )
                    lift = association_metrics_engine.get_lift(
                        association_metrics,
                        source_product_key,
                        product_key,
                    )
                    pair_count = (
                        association_metrics_engine.get_pair_count(
                            association_metrics,
                            source_product_key,
                            product_key,
                        )
                    )

                    best_confidence = max(
                        best_confidence, confidence
                    )
                    best_lift = max(best_lift, lift)
                    best_pair_count = max(
                        best_pair_count, pair_count
                    )

                if (
                    best_pair_count >= 2
                    and best_confidence >= 0.10
                ):
                    score += 10
                    reasons.append(
                        f"Historical association confidence is {best_confidence:.1%}"
                    )
                elif best_pair_count >= 1 and best_lift > 1:
                    score += 5
                    reasons.append(
                        f"Historical association lift is {best_lift:.2f}"
                    )

            # Configured relationship evidence.
            if candidate.get("relationship_source") == "configured":
                try:
                    strength = float(
                        candidate.get("relationship_strength", 0)
                    )
                except (TypeError, ValueError):
                    strength = 0

                # Invalid strengths should not add scoring points.
                strength = max(0.0, min(100.0, strength))
                score += round(strength * 0.30)

                relationship_reason = candidate.get(
                    "relationship_reason"
                )
                if relationship_reason:
                    reasons.append(str(relationship_reason))

                reasons.append(
                    f"Configured relationship strength: {strength:.0f}/100"
                )

        elif candidate_type == "QUOTATION":
            quotation_count = feature.get("quotation_count", 0)

            if quotation_count > 0:
                score += 25
                reasons.append(
                    f"Product appears in {quotation_count} quotation records"
                )

        return {
            **candidate,
            "score": min(score, 100),
            "reasons": reasons,
        }

    def score_candidates(
        self,
        candidates,
        customer_features=None,
        association_metrics_engine=None,
        association_metrics=None,
    ):
        scored_candidates = [
            self.score_candidate(
                candidate=candidate,
                customer_features=customer_features,
                association_metrics_engine=association_metrics_engine,
                association_metrics=association_metrics,
            )
            for candidate in candidates
        ]

        return sorted(
            scored_candidates,
            key=lambda candidate: candidate["score"],
            reverse=True,
        )
