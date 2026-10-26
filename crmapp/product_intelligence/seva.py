
from crmapp.models import Product
from .bucketing import ProductBucketer, SevaBucketRules


def get_seva_bucketed_products():
    """Return SEVA products with their assigned category buckets."""
    products = Product.objects.all()

    bucketer = ProductBucketer(rule_provider=SevaBucketRules)

    return bucketer.bucket_products(products)
