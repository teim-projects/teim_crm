class ProductEligibility:
    """
    CRM-independent product eligibility rules.

    The shared core accepts configurable excluded product keys and
    names. CRM-specific policies can supply these values without
    changing the recommendation engine.
    """

    def __init__(
        self,
        excluded_product_keys=None,
        excluded_product_names=None,
    ):
        self.excluded_product_keys = {
            str(key).strip().lower()
            for key in (excluded_product_keys or [])
            if key is not None and str(key).strip()
        }

        self.excluded_product_names = {
            str(name).strip().casefold()
            for name in (excluded_product_names or [])
            if name is not None and str(name).strip()
        }

    @staticmethod
    def _product_key(product):
        key = product.get("product_key")

        if key:
            return str(key).strip().lower()

        source_crm = str(
            product.get("source_crm") or ""
        ).strip().lower()

        source_product_id = product.get(
            "source_product_id",
            product.get("product_id"),
        )

        if not source_crm or source_product_id is None:
            return None

        source_product_id = str(source_product_id).strip()

        if not source_product_id:
            return None

        return f"{source_crm}:{source_product_id}"

    def is_eligible(self, product):
        """Return whether a product passes the configured exclusions."""
        if not isinstance(product, dict):
            return False

        product_key = self._product_key(product)

        if (
            product_key is not None
            and product_key in self.excluded_product_keys
        ):
            return False

        product_name = str(
            product.get("product_name") or ""
        ).strip().casefold()

        if product_name in self.excluded_product_names:
            return False

        return True

    def filter_products(self, products):
        """Return eligible products without modifying the input."""
        return [
            product
            for product in products
            if self.is_eligible(product)
        ]