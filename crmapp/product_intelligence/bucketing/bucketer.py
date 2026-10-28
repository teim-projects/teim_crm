class ProductBucketer:
    """
    CRM-independent product bucketing engine.

    The bucketer does not contain CRM-specific product rules.
    CRM-specific rules are supplied through the rule_provider.
    """

    def __init__(self, rule_provider=None):
        self.rule_provider = rule_provider

    def get_bucket(self, product):
        """
        Determine the bucket for a product using the supplied
        CRM-specific rule provider.
        """
        if self.rule_provider:
            return self.rule_provider.get_bucket(product)

        return "Uncategorized"

    def bucket_products(self, products):
        """
        Assign a bucket to every product.

        Returns:
            list[dict]
        """
        result = []

        for product in products:
            result.append({
                "product_id": self._get_value(product, "product_id"),
                "product_name": self._get_value(product, "product_name"),
                "category": self._get_value(product, "category"),
                "bucket": self.get_bucket(
                    self._to_dict(product)
                ),
            })

        return result

    @staticmethod
    def _to_dict(product):
        if isinstance(product, dict):
            return product

        return {
            "product_id": getattr(product, "product_id", None),
            "product_name": getattr(product, "product_name", None),
            "category": getattr(product, "category", None),
        }

    @staticmethod
    def _get_value(obj, field):
        if isinstance(obj, dict):
            return obj.get(field)

        return getattr(obj, field, None)
