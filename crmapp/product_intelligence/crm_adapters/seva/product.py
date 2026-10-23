
from crmapp.models import Product
from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class SevaProductAdapter:
    """Convert SEVA products into the common product format."""

    SOURCE_CRM = "seva"

    def get_all_products(self):
        return Product.objects.all()

    def get_product(self, product_id):
        return Product.objects.filter(
            product_id=product_id
        ).first()

    def to_universal_product(self, product):
        identity = UniversalProductIdentity.build(
            source_crm=self.SOURCE_CRM,
            source_product_id=product.product_id,
        )

        return {
            "product_id": product.product_id,
            "product_name": product.product_name,
            "category": product.category,
            **identity,
        }

    def get_universal_products(self):
        return [
            self.to_universal_product(product)
            for product in self.get_all_products()
        ]
