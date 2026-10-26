class SevaCompatibilityRules:
    """
    SEVA-specific product compatibility rules.

    These are explicit product relationships based on the actual
    SEVA Product Master. The reusable compatibility engine does
    not contain SEVA-specific product knowledge.
    """

    RULES = {
        # Cockroach-related products
        1: [27, 28, 29, 30],       # Cockroach Management

        # Rodent-related products
        8: [31, 34, 39],           # Rodent Management

        # Fly-related products
        44: [12, 25, 26, 68, 71, 97],  # Fly Management

        # Mosquito service variants
        6: [7, 64, 69],             # Mosquito Management (Spraying)
        7: [6, 64, 69],             # Mosquito Management (Fogging)
        64: [6, 7, 69],             # Mosquito Management Service
        69: [6, 7, 64],             # Mosquito Spray & Anti Larval Treatment Service

        # Fumigation / storage-related products
        49: [50, 51, 52],            # Self Verifying Cocoons 10MT
        50: [49, 51, 52],            # Cocoon Flush Hose Pipe
        51: [49, 50, 52],            # O2 Analyser Machine
        52: [49, 50, 51],            # Manual Aspirator With Adapter
    }

    @classmethod
    def get_compatible_products(cls, product_id):
        return cls.RULES.get(product_id, [])

    @classmethod
    def is_compatible(cls, source_product_id, candidate_product_id):
        if source_product_id == candidate_product_id:
            return False

        return candidate_product_id in cls.RULES.get(
            source_product_id,
            []
        )
