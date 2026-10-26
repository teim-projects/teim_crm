
class ProductBucketer:
    """
    CRM-independent product bucketing engine.

    The common engine receives bucket definitions from the CRM-specific
    configuration. It does not contain SEVA-specific product rules.
    """

    def __init__(self, bucket_map=None):
        self.bucket_map = bucket_map or {}

    @staticmethod
    def _get_value(product, field):
        if isinstance(product, dict):
            return product.get(field)
        return getattr(product, field, None)

    def get_bucket(self, product):
        product_id = self._get_value(product, "product_id")

        for bucket, product_ids in self.bucket_map.items():
            if product_id in product_ids:
                return bucket

        category = self._get_value(product, "category")
        return category or "Uncategorized"

    def bucket_products(self, products):
        results = []

        for product in products:
            results.append({
                "product_id": self._get_value(product, "product_id"),
                "product_name": self._get_value(product, "product_name"),
                "category": self._get_value(product, "category"),
                "bucket": self.get_bucket(product),
            })

        return results
