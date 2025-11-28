# utils.py
from crmapp.models import Branch
from django.db import IntegrityError, transaction
from typing import Any, Dict, Optional
from django.db.models import QuerySet

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
