from crmapp.models import Product


def get_seva_bucket_map():
    buckets = {}

    for product in Product.objects.all():
        bucket = product.category or "Uncategorized"
        buckets.setdefault(bucket, []).append(product.product_id)

    return buckets
