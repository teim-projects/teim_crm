class AMCRecommendationEngine:
    """
    CRM-independent AMC recommendation engine.

    Uses actual AMC service-visit history supplied by the CRM adapter.

    The engine identifies products repeatedly serviced under AMC
    and converts that history into recommendation signals.

    It does not assume renewal dates, contract status, frequency,
    or completion status unless those values are explicitly supplied.
    """

    def build_customer_amc_features(self, customer_id, amc_products):
        product_data = {}

        for record in amc_products:
            if record.get("customer_id") != customer_id:
                continue

            product_id = record.get("product_id")

            if product_id is None:
                continue

            if product_id not in product_data:
                product_data[product_id] = {
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "visit_count": 0,
                    "amc_ids": set(),
                    "visit_ids": set(),
                }

            data = product_data[product_id]

            data["visit_count"] += 1

            if record.get("amc_id") is not None:
                data["amc_ids"].add(record["amc_id"])

            if record.get("visit_id") is not None:
                data["visit_ids"].add(record["visit_id"])

        features = []

        for data in product_data.values():
            features.append({
                "customer_id": data["customer_id"],
                "product_id": data["product_id"],
                "visit_count": data["visit_count"],
                "amc_count": len(data["amc_ids"]),
                "unique_visit_count": len(data["visit_ids"]),
            })

        return sorted(
            features,
            key=lambda item: item["product_id"]
        )

    def generate_recommendations(
        self,
        customer_id,
        amc_products,
        existing_product_ids=None,
    ):
        existing_product_ids = set(existing_product_ids or [])

        features = self.build_customer_amc_features(
            customer_id,
            amc_products,
        )

        recommendations = []

        for feature in features:
            product_id = feature["product_id"]

            if product_id in existing_product_ids:
                continue

            visit_count = feature["visit_count"]

            if visit_count >= 25:
                score = 40
                reason = (
                    f"Product has {visit_count} AMC service visits"
                )
            elif visit_count >= 10:
                score = 30
                reason = (
                    f"Product has {visit_count} AMC service visits"
                )
            elif visit_count >= 3:
                score = 20
                reason = (
                    f"Product has {visit_count} AMC service visits"
                )
            else:
                score = 10
                reason = (
                    f"Product has {visit_count} AMC service visit"
                )

            recommendations.append({
                "customer_id": customer_id,
                "product_id": product_id,
                "recommendation_type": "AMC_REPEAT",
                "score": score,
                "reasons": [reason],
                "amc_visit_count": visit_count,
                "amc_count": feature["amc_count"],
            })

        return sorted(
            recommendations,
            key=lambda item: (
                -item["score"],
                item["product_id"],
            ),
        )
