# utils.py
from crmapp.models import Branch
from django.db import IntegrityError, transaction

def get_destination_queryset(dest_type: str):
    """
    Return a queryset for the requested destination type.
    We import Site lazily to avoid circular import issues if Site lives in new_inventory.models.
    """
    if dest_type == "HO":
        return Branch.objects.filter(is_head_office=True)
    elif dest_type == "BRANCH":
        return Branch.objects.filter(is_head_office=False)
    elif dest_type == "SITE":
        # Lazy import to avoid circular import problems
        from new_inventory.models import Site
        return Site.objects.all()
    return Branch.objects.none()


def get_destination_object(dest_type, dest_id):
    """Return the destination object (or None) given a type and an id."""
    qs = get_destination_queryset(dest_type)
    try:
        return qs.get(pk=dest_id)
    except Exception:
        return None


def get_or_create_product_batch(product, batch=None, batch_no_str=None, manufacturing_date=None, expiry_date=None):
    """
    Returns a ProductBatch instance.

    Behavior:
      - If `batch` (Batch instance) provided, try to get_or_create ProductBatch for that Batch+Product.
      - Else if batch_no_str provided, get_or_create Batch by batch_no then get/create ProductBatch.
      - Else create a new Batch and ProductBatch.

    This function uses lazy imports to avoid circular import / NameError issues.
    It also handles IntegrityError race conditions by retrying a lookup.
    """
    # Lazy import models to avoid circular import at module import time
    from new_inventory.models import Batch, ProductBatch

    try:
        with transaction.atomic():
            # Determine batch object
            if batch is None:
                if batch_no_str:
                    batch_obj, _ = Batch.objects.get_or_create(batch_no=batch_no_str)
                else:
                    batch_obj = Batch.objects.create()
            else:
                batch_obj = batch

            # Get or create ProductBatch for (product, batch_obj)
            product_batch, created = ProductBatch.objects.get_or_create(
                product=product,
                batch=batch_obj,
                defaults={
                    "manufacturing_date": manufacturing_date,
                    "expiry_date": expiry_date,
                }
            )

            # If ProductBatch existed but dates were provided, fill missing dates
            changed = False
            if manufacturing_date and not product_batch.manufacturing_date:
                product_batch.manufacturing_date = manufacturing_date
                changed = True
            if expiry_date and not product_batch.expiry_date:
                product_batch.expiry_date = expiry_date
                changed = True
            if changed:
                product_batch.save()

            return product_batch

    except IntegrityError:
        # Race condition: another process created the same record at the same time.
        # Try to fetch it instead of failing.
        try:
            return ProductBatch.objects.get(product=product, batch=batch_obj)
        except ProductBatch.DoesNotExist:
            # If it truly doesn't exist, re-raise the error so caller can see it
            raise
