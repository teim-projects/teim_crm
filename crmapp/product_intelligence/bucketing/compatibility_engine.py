class ProductCompatibilityEngine:
    """
    CRM-independent compatibility engine.

    Compatibility rules are supplied externally so that the
    reusable engine contains no SEVA-specific product knowledge.
    """

    def __init__(self, rule_provider):
        self.rule_provider = rule_provider

    def is_compatible(self, source_product_id, candidate_product_id):
        return self.rule_provider.is_compatible(
            source_product_id,
            candidate_product_id,
        )

    def get_compatible_products(self, source_product_id):
        return self.rule_provider.get_compatible_products(
            source_product_id
        )

    def filter_candidates(self, source_product_ids, candidate_product_ids):
        source_product_ids = set(source_product_ids or [])
        candidate_product_ids = set(candidate_product_ids or [])

        compatible = set()

        for source_product_id in source_product_ids:
            compatible.update(
                self.get_compatible_products(source_product_id)
            )

        return sorted(
            compatible.intersection(candidate_product_ids)
        )
