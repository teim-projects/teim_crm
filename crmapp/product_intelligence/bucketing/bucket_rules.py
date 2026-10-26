class SevaBucketRules:
    """
    SEVA-specific product bucket rules.

    These rules use the actual category values present in the
    SEVA Product master.
    """

    CATEGORY_MAP = {
        "PestControl": "Pest Control",
        "Pest Control": "Pest Control",
        "Fumigation": "Fumigation",
        "Product Sale": "Product Sale",
    }

    @classmethod
    def get_bucket(cls, product):
        category = product.get("category")

        return cls.CATEGORY_MAP.get(
            category,
            "Uncategorized"
        )
