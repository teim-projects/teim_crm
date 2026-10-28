class ProductUpsellEngine:
    """
    CRM-independent upselling engine.

    CRM-specific upgrade relationships are supplied through
    the rule provider.

    The engine does not assume that a larger, newer, or different
    product is automatically an upsell.
    """

    def __init__(self, rule_provider):
        self.rule_provider = rule_provider

    def is_upsell(self, source_product_id, candidate_product_id):
        return self.rule_provider.is_upsell(
            source_product_id,
            candidate_product_id,
        )

    def get_upsell_products(self, source_product_id):
        return self.rule_provider.get_upsell_products(
            source_product_id
        )

    def generate_candidates(
        self,
        source_product_ids,
        candidate_product_ids,
    ):
        source_product_ids = set(source_product_ids or [])
        candidate_product_ids = set(candidate_product_ids or [])

        candidates = set()

        for source_product_id in source_product_ids:
            candidates.update(
                self.get_upsell_products(source_product_id)
            )

        return sorted(
            candidates.intersection(candidate_product_ids)
        )
