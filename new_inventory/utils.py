# utils.py
from crmapp.models import Branch
from django.db import IntegrityError, transaction
from typing import Any, Dict, Optional
from django.db.models import QuerySet
from django.db.models import Sum, F,Q
from django.db.models import Q, Sum as DJSum, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import timedelta, date
from collections import OrderedDict
from .models import *


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

# get exact destination 
def get_destination_object(dest_type, dest_id):
    """Return the destination object (or None) given a type and an id."""
    qs = get_destination_queryset(dest_type)
    try:
        return qs.get(pk=dest_id)
    except Exception:
        return None



def get_destination_details(dest_type: str, dest_id: Any) -> Optional[Dict[str, Any]]:
    if not dest_type or not dest_id:
        return None

    dest = get_destination_object(dest_type, dest_id)
    if not dest:
        return None

    # Helper to safely getattr and cast to str when needed
    def _str_attr(o, *names):
        for n in names:
            v = getattr(o, n, None)
            if v not in (None, ""):
                return str(v)
        return ""

    details: Dict[str, Any] = {
        "type": dest_type,
        "id": dest_id,
        "name": "",
        "address": "",
        "contact_person": "",
        "phone": "",
        "phone2": "",
        "email1": "",
        "email2": "",
        "gstin": "",
        "pan": "",
        "code": "",
        "shortcut": "",
        "is_head_office": False,
        "raw": dest,
    }

    # Branch-like objects (Branch has branch_name, full_address, contact_1, contact_2, etc.)
    if dest_type in ("HO", "BRANCH"):
        # name
        details["name"] = _str_attr(dest, "branch_name", "name")
        # address
        details["address"] = _str_attr(dest, "full_address", "address", "addr", "location")
        # contacts
        details["phone"] = _str_attr(dest, "contact_1", "contact", "phone", "phone_no")
        details["phone2"] = _str_attr(dest, "contact_2", "phone2")
        # emails
        details["email1"] = _str_attr(dest, "email_1", "email")
        details["email2"] = _str_attr(dest, "email_2")
        # gst, pan
        details["gstin"] = _str_attr(dest, "gst_number", "gstin", "gst")
        details["pan"] = _str_attr(dest, "pan_number", "pan")
        # code / shortcut / is_head_office
        details["code"] = _str_attr(dest, "code", "branch_code", "id")
        details["state"] = _str_attr(dest, "state", "branch_state")
        details["shortcut"] = _str_attr(dest, "shortcut")
        details["is_head_office"] = bool(getattr(dest, "is_head_office", False))

    # Site-like objects
    elif dest_type == "SITE":
        details["name"] = _str_attr(dest, "name", "site_name", "location_name")
        details["address"] = _str_attr(dest, "address", "full_address", "addr")
        details["contact_person"] = _str_attr(dest, "contact_person", "contact")
        details["phone"] = _str_attr(dest, "phone", "contact_no", "contact_1")
        # Sites probably don't have gst/pan/shortcut fields; leave them empty
        details["code"] = _str_attr(dest, "id", "code", "site_code")

    # Fallback: if nothing filled, try sensible __str__
    if not details["name"]:
        details["name"] = _str_attr(dest, "name") or str(dest)

    return details


def format_destination_display(details: Dict[str, Any]) -> str:
    if not details:
        return "Not specified"

    parts = []
    if details.get("name"):
        parts.append(details["name"])
    if details.get("address"):
        parts.append(details["address"])
    if details.get("state"):
        parts.append(details["state"])
    if details.get("code"):
        parts.append(f"({details['code']})")
    if details.get("gstin"):
        parts.append(f"GSTIN: {details['gstin']}")
    if details.get("phone"):
        parts.append(f"Phone: {details['phone']}")

    return " | ".join(parts) if parts else "Not specified"


# product batch 
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










def _parse_date(val):
    if not val:
        return None
    if isinstance(val, (date,)):
        return val
    try:
        return date.fromisoformat(val)
    except Exception:
        return None

def annotated_product_stock_qs(ProductModel, location_type=None, location_id=None, search=None,
                               batch_no=None, expiry_from=None, expiry_to=None):
    """
    Return a Product queryset annotated with aggregated stock totals.
    If batch_no or expiry_from/expiry_to supplied -> annotate batch-scoped totals from CurrentStock (subquery).
    Otherwise annotate denormalized ProductStock sums (fast).
    """
    # normalize expiry dates (accept 'YYYY-MM-DD' strings)
    expiry_from_date = _parse_date(expiry_from)
    expiry_to_date = _parse_date(expiry_to)
    from .models import CurrentStock
    # base ProductStock filter (used only for productstock aggregates)
    ps_filter = Q()
    if location_type:
        ps_filter &= Q(productstock__location_type=location_type)
    if location_id is not None:
        ps_filter &= Q(productstock__location_id=location_id)

    qs = ProductModel.objects.all()

    # search by product_name
    if search:
        qs = qs.filter(Q(product_name__icontains=search))

    # If batch/expiry filters are present, build a CurrentStock subquery that aggregates per-product totals
    use_batch_annotation = bool(batch_no or expiry_from_date or expiry_to_date)
    if use_batch_annotation:
        # Build the subquery filter for CurrentStock
        cs_qs = CurrentStock.objects.filter(product_id=OuterRef('pk'))

        if batch_no:
            cs_qs = cs_qs.filter(batch__batch__batch_no__iexact=batch_no)

        if expiry_from_date:
            cs_qs = cs_qs.filter(batch__expiry_date__gte=expiry_from_date)
        if expiry_to_date:
            cs_qs = cs_qs.filter(batch__expiry_date__lte=expiry_to_date)

        # If you also want to restrict to a location (CurrentStock stores location_type/id), apply it
        if location_type:
            cs_qs = cs_qs.filter(location_type=location_type)
        if location_id is not None:
            cs_qs = cs_qs.filter(location_id=location_id)

        # Aggregate per product. Use the per-batch in_qty field (change 'in_qty' if your field is different)
        cs_agg = cs_qs.values('product_id').annotate(total_in=DJSum('in_qty')).values('total_in')

        # Annotate product with batch-scoped total
        qs = qs.annotate(
            batch_in_qty=Coalesce(Subquery(cs_agg, output_field=None), Decimal('0.000'))
        )

        # Also annotate batch-scoped reserved/out if needed (example for reserved: uncomment if you have those fields)
        # cs_agg_reserved = cs_qs.values('product_id').annotate(total_reserved=DJSum('reserved_qty')).values('total_reserved')
        # qs = qs.annotate(batch_reserved_qty=Coalesce(Subquery(cs_agg_reserved), Decimal('0.000')))

    # Always annotate denormalized ProductStock totals (fast) — used when not filtering by batch/expiry
    qs = qs.annotate(
        in_qty=Coalesce(DJSum('productstock__total_in_qty', filter=ps_filter), Decimal('0.000')),
        out_qty=Coalesce(DJSum('productstock__total_out_qty', filter=ps_filter), Decimal('0.000')),
        reserved_qty=Coalesce(DJSum('productstock__total_reserved_qty', filter=ps_filter), Decimal('0.000')),
    )

    # If batch filters were provided, optionally restrict which products appear:
    # - If you want only products that have matching CurrentStock (matching batch/expiry), filter by that existence:
    if use_batch_annotation:
        qs = qs.filter(currentstock__batch__batch__batch_no__iexact=batch_no) if batch_no else qs
        if expiry_from_date:
            qs = qs.filter(currentstock__batch__expiry_date__gte=expiry_from_date)
        if expiry_to_date:
            qs = qs.filter(currentstock__batch__expiry_date__lte=expiry_to_date)
        # If location filters, apply them too to limit results to products that have CS in that location
        if location_type:
            qs = qs.filter(currentstock__location_type=location_type)
        if location_id is not None:
            qs = qs.filter(currentstock__location_id=location_id)

    return qs.distinct()
