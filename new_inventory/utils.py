# utils.py
from django.db import IntegrityError, transaction
from typing import Any, Dict, Optional
from django.db.models import QuerySet
from django.db.models import Sum, F, Q
from django.db.models import Q, Sum as DJSum, OuterRef, Subquery, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import timedelta, date
from collections import OrderedDict

# crmapp cross-app imports (no circular issue — crmapp does not import new_inventory.utils)
from crmapp.models import Branch, BranchManager

# NOTE: new_inventory.models imports THIS file (utils.py), so we CANNOT import
# new_inventory models at module level — it causes a circular import.
# All new_inventory model imports are done lazily inside each function that needs them.



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
        "manager_name": "",
        "manager_phone": "",
        "manager_email": "",

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

        # ---- Branch Manager details (CRM) ----
        # IMPORTANT: HO is also a Branch → always fetch manager
        if dest_type in ("HO", "BRANCH"):
            manager = (
                BranchManager.objects
                .filter(branch=dest)
                .order_by("-id")
                .first()
            )

            if manager:
                details["contact_person"] = manager.full_name
                details["phone"] = manager.mobile_no
                details["email1"] = manager.email

                details["manager_name"] = manager.full_name
                details["manager_phone"] = manager.mobile_no
                details["manager_email"] = manager.email




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

    # ── Annotate approved_qty from StockLedger (SERVICE_OUT net of SERVICE_RETURN/REVERSAL) ──
    # This avoids any new DB column — computed directly from existing ledger data.
    from .models import StockLedger

    # Build StockLedger filter for SERVICE_OUT per product
    sl_out_filter = Q(product_id=OuterRef('pk'), transaction_type='SERVICE_OUT')
    sl_ret_filter = Q(product_id=OuterRef('pk'), transaction_type__in=['SERVICE_RETURN', 'SERVICE_REVERSAL'])
    if location_type:
        sl_out_filter &= Q(location_type=location_type)
        sl_ret_filter &= Q(location_type=location_type)
    if location_id is not None:
        sl_out_filter &= Q(location_id=location_id)
        sl_ret_filter &= Q(location_id=location_id)

    service_out_subq = (
        StockLedger.objects.filter(sl_out_filter)
        .values('product_id')
        .annotate(total=DJSum('out_qty'))
        .values('total')
    )
    service_ret_subq = (
        StockLedger.objects.filter(sl_ret_filter)
        .values('product_id')
        .annotate(total=DJSum('in_qty'))
        .values('total')
    )

    qs = qs.annotate(
        approved_qty=(
            Coalesce(Subquery(service_out_subq), Decimal('0.000')) -
            Coalesce(Subquery(service_ret_subq), Decimal('0.000'))
        )
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




# ─────────────────────────────────────────────────────────────────────────────
# SERVICE APPROVAL STOCK DEDUCTION
# ─────────────────────────────────────────────────────────────────────────────

def _get_service_location(service):
    """
    Returns (location_type, location_id) for stock deduction based on the
    branch/location that the service is assigned to.

    Rules:
      - If the service has a branch and that branch IS the Head Office  → ("HO",   branch.id)
      - If the service has a branch and that branch is NOT Head Office  → ("BRANCH", branch.id)
      - If no branch is set on the service                              → fallback to HO
    """
    from crmapp.models import Branch

    branch = getattr(service, "branch", None)

    if branch is not None:
        # The service has an assigned branch — use it directly.
        if branch.is_head_office:
            return "HO", branch.id
        else:
            return "BRANCH", branch.id

    # No branch linked to this service — fall back to HO as a safe default.
    ho = Branch.objects.filter(is_head_office=True).first()
    if ho:
        return "HO", ho.id

    # Last resort — should never reach here in a properly seeded DB.
    return "HO", 1


# ─────────────────────────────────────────────────────────────────────────────
# SUB-ITEM HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _sub_item_ref(service_id, required_item_id):
    """Unique ledger transaction_ref for a sub-item deduction."""
    return f"SERVICE_{service_id}_SUBITEM_{required_item_id}"


def _get_sub_item_available_qty(required_item_id, location_type, location_id):
    """
    Compute how much of a sub-item (ProductRequiredItem) is available at a
    given location.

    Available = total received via GRN at this location
               - total already consumed (SERVICE_OUT ledger entries for this sub-item)

    Sub-items don't have a CurrentStock row, so we compute live from:
      - GoodsReceiveNoteSubItem  (IN stock)
      - StockLedger entries with transaction_ref ending in SUBITEM_{id}  (OUT)
    """
    from .models import GoodsReceiveNoteSubItem, StockLedger
    from django.db.models import Sum as DSum

    total_in = (
        GoodsReceiveNoteSubItem.objects.filter(
            sub_item_id=required_item_id,
            grn__destination_type=location_type,
            grn__destination_id=location_id,
        ).aggregate(total=DSum("received_qty"))["total"]
        or Decimal("0.000")
    )

    # All SERVICE_OUT ledger rows for this sub-item at this location
    ref_suffix = f"SUBITEM_{required_item_id}"
    total_out = (
        StockLedger.objects.filter(
            transaction_type="SERVICE_OUT",
            transaction_ref__endswith=ref_suffix,
            location_type=location_type,
            location_id=location_id,
        ).aggregate(total=DSum("out_qty"))["total"]
        or Decimal("0.000")
    )

    # Also subtract SERVICE_RETURN (stock returned back after a service)
    total_returned = (
        StockLedger.objects.filter(
            transaction_type="SERVICE_RETURN",
            transaction_ref__endswith=ref_suffix,
            location_type=location_type,
            location_id=location_id,
        ).aggregate(total=DSum("in_qty"))["total"]
        or Decimal("0.000")
    )

    return max(Decimal("0.000"), Decimal(str(total_in)) - Decimal(str(total_out)) + Decimal(str(total_returned)))


def deduct_stock_for_service(service, user):
    """
    Deducts inventory stock for every product AND sub-item linked to the service
    on approval.

    Products  → FIFO CurrentStock deduction, StockLedger ref=SERVICE_{id}
    Sub-items → GRN-based availability, StockLedger ref=SERVICE_{id}_SUBITEM_{ri_id}

    Returns:
        list[str] — warning messages (empty = everything deducted successfully)
    """
    from .models import CurrentStock, ProductStock, StockLedger

    warnings = []
    location_type, location_id = _get_service_location(service)

    with transaction.atomic():
        service_products = (
            service.service_products
            .select_related('product')
            .prefetch_related('selected_items__required_item')
            .all()
        )

        if not service_products.exists():
            warnings.append("No products linked to this service — nothing to deduct.")
            return warnings

        for sp in service_products:
            product    = sp.product
            qty_needed = Decimal(str(sp.quantity))

            # ── PART A: Deduct parent PRODUCT from CurrentStock ───────────────
            stock_rows = CurrentStock.objects.select_for_update().filter(
                product=product,
                location_type=location_type,
                location_id=location_id,
            ).order_by('id')  # FIFO

            if not stock_rows.exists():
                warnings.append(
                    f"'{product.product_name}': No stock at {location_type} "
                    f"(id={location_id}). Deduction skipped."
                )
            else:
                total_available = sum(cs.available_qty for cs in stock_rows)
                if total_available < qty_needed:
                    warnings.append(
                        f"'{product.product_name}': Low stock — need {qty_needed}, "
                        f"available {total_available}. Deducting what is available."
                    )

                remaining = qty_needed
                for stock in stock_rows:
                    if remaining <= Decimal('0'):
                        break
                    can_take = min(stock.available_qty, remaining)
                    if can_take <= Decimal('0'):
                        continue

                    stock.out_qty = (stock.out_qty or Decimal('0')) + can_take
                    stock.recompute_closing()

                    StockLedger.objects.create(
                        product=product,
                        batch=stock.batch,
                        location_type=location_type,
                        location_id=location_id,
                        transaction_type="SERVICE_OUT",
                        transaction_ref=f"SERVICE_{service.id}",
                        document_id=service.id,
                        in_qty=Decimal('0.000'),
                        out_qty=can_take,
                        balance_qty=stock.closing_qty,
                        created_by=user,
                        remarks=(
                            f"Service #{service.id} approval — "
                            f"{product.product_name} x{can_take}"
                            + (f" [batch: {stock.batch}]" if stock.batch else "")
                        ),
                    )
                    remaining -= can_take

                ps, _ = ProductStock.objects.select_for_update().get_or_create(
                    product=product,
                    location_type=location_type,
                    location_id=location_id,
                    defaults={
                        'total_in_qty': Decimal('0.000'),
                        'total_out_qty': Decimal('0.000'),
                        'total_reserved_qty': Decimal('0.000'),
                    },
                )
                actually_deducted = qty_needed - remaining
                ps.total_out_qty = max(
                    Decimal('0.000'),
                    (ps.total_out_qty or Decimal('0')) + actually_deducted
                )
                ps.save(update_fields=['total_out_qty', 'updated_at'])

            # ── PART B: Deduct each SUB-ITEM linked to this ServiceProduct ────
            for spi in sp.selected_items.all():
                required_item    = spi.required_item
                sub_qty_needed   = Decimal(str(spi.quantity))
                sub_remaining    = sub_qty_needed          # own variable — never touches product's 'remaining'
                ref              = _sub_item_ref(service.id, required_item.id)

                available = _get_sub_item_available_qty(
                    required_item.id, location_type, location_id
                )

                if available <= Decimal('0'):
                    warnings.append(
                        f"Sub-item '{required_item.item_name}' "
                        f"(for {product.product_name}): "
                        f"No stock at {location_type} (id={location_id}). Skipped."
                    )
                    continue

                sub_can_take = min(available, sub_qty_needed)
                if sub_can_take < sub_qty_needed:
                    warnings.append(
                        f"Sub-item '{required_item.item_name}' "
                        f"(for {product.product_name}): "
                        f"Low stock — need {sub_qty_needed}, available {available}."
                    )

                StockLedger.objects.create(
                    product=product,         # parent product FK (non-nullable)
                    batch=None,              # sub-items are not batch-tracked
                    location_type=location_type,
                    location_id=location_id,
                    transaction_type="SERVICE_OUT",
                    transaction_ref=ref,     # SERVICE_{id}_SUBITEM_{ri_id}
                    document_id=service.id,
                    in_qty=Decimal('0.000'),
                    out_qty=sub_can_take,
                    balance_qty=Decimal('0.000'),  # sub-items have no CurrentStock row
                    created_by=user,
                    remarks=(
                        f"Service #{service.id} approval — "
                        f"sub-item '{required_item.item_name}' x{sub_can_take} "
                        f"(for {product.product_name})"
                    ),
                )
                sub_remaining -= sub_can_take  # track sub-item's own remaining (for future use)

    return warnings


def reverse_stock_for_service(service, user):
    """
    Reverses stock deductions when a service is rejected / un-approved.

    Handles both product (CurrentStock) and sub-item (ledger-only) entries.

    Returns:
        list[str] — warning messages
    """
    from .models import CurrentStock, ProductStock, StockLedger

    warnings = []

    with transaction.atomic():
        # ── PART A: Reverse PRODUCT entries (exact ref match) ─────────────────
        product_entries = StockLedger.objects.select_for_update().filter(
            transaction_ref=f"SERVICE_{service.id}",
            transaction_type="SERVICE_OUT",
        )

        sub_item_entries = StockLedger.objects.select_for_update().filter(
            transaction_ref__startswith=f"SERVICE_{service.id}_SUBITEM_",
            transaction_type="SERVICE_OUT",
        )

        if not product_entries.exists() and not sub_item_entries.exists():
            warnings.append(
                f"No SERVICE_OUT ledger entries found for service #{service.id}. "
                "Nothing to reverse."
            )
            return warnings

        for entry in product_entries:
            qty_to_return = entry.out_qty
            product       = entry.product

            stock_qs = CurrentStock.objects.select_for_update().filter(
                product=product,
                batch=entry.batch,
                location_type=entry.location_type,
                location_id=entry.location_id,
            )

            if stock_qs.exists():
                stock = stock_qs.first()
                stock.out_qty = max(
                    Decimal('0.000'),
                    (stock.out_qty or Decimal('0')) - qty_to_return
                )
                stock.recompute_closing()
                closing_for_ledger = stock.closing_qty
            else:
                warnings.append(
                    f"'{product.product_name}': Original stock record not found "
                    f"(batch={entry.batch}). Reversal skipped."
                )
                continue

            ps_qs = ProductStock.objects.select_for_update().filter(
                product=product,
                location_type=entry.location_type,
                location_id=entry.location_id,
            )
            if ps_qs.exists():
                ps = ps_qs.first()
                ps.total_out_qty = max(
                    Decimal('0.000'),
                    (ps.total_out_qty or Decimal('0')) - qty_to_return
                )
                ps.save(update_fields=['total_out_qty', 'updated_at'])

            StockLedger.objects.create(
                product=product,
                batch=entry.batch,
                location_type=entry.location_type,
                location_id=entry.location_id,
                transaction_type="SERVICE_REVERSAL",
                transaction_ref=f"SERVICE_{service.id}",
                document_id=service.id,
                in_qty=qty_to_return,
                out_qty=Decimal('0.000'),
                balance_qty=closing_for_ledger,
                created_by=user,
                remarks=(
                    f"Reversal for service #{service.id} — "
                    f"{product.product_name} x{qty_to_return} returned"
                ),
            )

        # ── PART B: Reverse SUB-ITEM entries (ledger-only, no CurrentStock) ──
        for entry in sub_item_entries:
            qty_to_return = entry.out_qty
            product       = entry.product

            StockLedger.objects.create(
                product=product,
                batch=None,
                location_type=entry.location_type,
                location_id=entry.location_id,
                transaction_type="SERVICE_REVERSAL",
                transaction_ref=entry.transaction_ref,   # keep SUBITEM ref
                document_id=service.id,
                in_qty=qty_to_return,
                out_qty=Decimal('0.000'),
                balance_qty=Decimal('0.000'),
                created_by=user,
                remarks=(
                    f"Reversal for service #{service.id} — "
                    f"sub-item x{qty_to_return} returned (ref: {entry.transaction_ref})"
                ),
            )

    return warnings


def get_service_stock_out_summary(service):
    """
    Returns a list of dicts describing what stock was deducted for a given service.
    Used to pre-fill the stock return form.

    Each dict:
      {
        'ledger_id'  : int         (StockLedger PK),
        'product'    : Product obj,
        'batch'      : Batch obj or None,
        'out_qty'    : Decimal     (what was taken out),
        'returned'   : Decimal     (already returned via SERVICE_RETURN),
        'returnable' : Decimal     (out_qty - returned, max that can still be returned),
        'location_type': str,
        'location_id'  : int,
      }
    """
    from .models import StockLedger

    out_entries = StockLedger.objects.filter(
        transaction_ref=f"SERVICE_{service.id}",
        transaction_type="SERVICE_OUT",
    ).select_related("product", "batch")

    # Sum already-returned per ledger entry (linked by document_id + batch + product)
    already_returned = StockLedger.objects.filter(
        transaction_ref=f"SERVICE_{service.id}",
        transaction_type="SERVICE_RETURN",
    ).values("product_id", "batch_id").annotate(total=Sum("in_qty"))

    returned_map = {
        (r["product_id"], r["batch_id"]): r["total"] for r in already_returned
    }

    rows = []
    for entry in out_entries:
        key = (entry.product_id, entry.batch_id)
        already = returned_map.get(key, Decimal("0.000"))
        returnable = max(Decimal("0.000"), entry.out_qty - already)
        rows.append({
            "ledger_id"    : entry.pk,
            "product"      : entry.product,
            "batch"        : entry.batch,
            "out_qty"      : entry.out_qty,
            "returned"     : already,
            "returnable"   : returnable,
            "location_type": entry.location_type,
            "location_id"  : entry.location_id,
        })
    return rows



def partial_return_stock_for_service(service, return_items, user):
    """
    Returns a SUBSET of deducted stock back to inventory after a service.

    Business rule:
      - If 5 was approved and technician returns 1 → approved becomes 4, available +1
      - Sub-items use spi_id (ServiceProductItem.pk) as the form key; they have no
        CurrentStock row so only a SERVICE_RETURN ledger entry is written.
      - Products use ledger_id; CurrentStock.out_qty is reduced and ProductStock updated.

    Args:
        service      : ServiceManagement instance
        return_items : list of dicts — either
                         { 'spi_id': int,    'return_qty': Decimal }  ← sub-item
                         { 'ledger_id': int, 'return_qty': Decimal }  ← product
        user         : User instance

    Returns:
        (list[str] warnings, list[str] errors)
    """
    from .models import CurrentStock, ProductStock, StockLedger

    warnings = []
    errors   = []

    with transaction.atomic():
        for item in return_items:
            return_qty = Decimal(str(item.get("return_qty", 0)))
            if return_qty <= Decimal("0"):
                continue

            spi_id    = item.get("spi_id")
            ledger_id = item.get("ledger_id")

            # ── PATH A: Sub-item return (keyed by ServiceProductItem.id) ──────────
            if spi_id:
                from crmapp.models import ServiceProductItem
                try:
                    spi = ServiceProductItem.objects.select_related(
                        "required_item", "service_product__product"
                    ).get(pk=spi_id, service_product__service=service)
                except ServiceProductItem.DoesNotExist:
                    errors.append(f"Sub-item #{spi_id} not found for this service.")
                    continue

                ri      = spi.required_item
                ref     = _sub_item_ref(service.id, ri.id)
                out_qty = Decimal(str(spi.quantity))

                already_returned = (
                    StockLedger.objects.filter(
                        transaction_ref=ref,
                        transaction_type="SERVICE_RETURN",
                    ).aggregate(total=Sum("in_qty"))["total"]
                    or Decimal("0")
                )
                max_returnable = max(Decimal("0"), out_qty - already_returned)
                if return_qty > max_returnable:
                    warnings.append(
                        f"\'{ri.item_name}\': return qty {return_qty} exceeds "
                        f"returnable {max_returnable}. Clamping."
                    )
                    return_qty = max_returnable

                if return_qty <= Decimal("0"):
                    continue

                location_type, location_id = _get_service_location(service)
                StockLedger.objects.create(
                    product=spi.service_product.product,
                    batch=None,
                    location_type=location_type,
                    location_id=location_id,
                    transaction_type="SERVICE_RETURN",
                    transaction_ref=ref,
                    document_id=service.id,
                    in_qty=return_qty,
                    out_qty=Decimal("0.000"),
                    balance_qty=Decimal("0.000"),
                    created_by=user,
                    remarks=(
                        f"Partial return service #{service.id} — "
                        f"sub-item \'{ri.item_name}\' x{return_qty} returned"
                    ),
                )
                continue  # sub-item done

            # ── PATH B: Product return (keyed by ledger_id) ───────────────────────
            if not ledger_id:
                errors.append("Row has neither ledger_id nor spi_id — skipped.")
                continue

            try:
                out_entry = StockLedger.objects.select_for_update().get(
                    pk=ledger_id,
                    transaction_type="SERVICE_OUT",
                    document_id=service.id,
                )
            except StockLedger.DoesNotExist:
                errors.append(f"Ledger entry #{ledger_id} not found for this service.")
                continue

            product = out_entry.product
            batch   = out_entry.batch

            already_returned = (
                StockLedger.objects.filter(
                    transaction_ref=out_entry.transaction_ref,
                    transaction_type="SERVICE_RETURN",
                    product=product,
                ).aggregate(total=Sum("in_qty"))["total"]
                or Decimal("0")
            )

            max_returnable = out_entry.out_qty - already_returned
            if return_qty > max_returnable:
                warnings.append(
                    f"Return qty {return_qty} exceeds returnable {max_returnable}. Clamping."
                )
                return_qty = max_returnable

            if return_qty <= Decimal("0"):
                continue

            # Reduce CurrentStock.out_qty → available_qty rises
            stock_qs = CurrentStock.objects.select_for_update().filter(
                product=product,
                batch=batch,
                location_type=out_entry.location_type,
                location_id=out_entry.location_id,
            )
            if stock_qs.exists():
                stock = stock_qs.first()
                stock.out_qty = max(
                    Decimal("0.000"),
                    (stock.out_qty or Decimal("0")) - return_qty,
                )
                stock.recompute_closing()
            else:
                stock = CurrentStock.objects.create(
                    product=product,
                    batch=batch,
                    location_type=out_entry.location_type,
                    location_id=out_entry.location_id,
                    in_qty=return_qty,
                    out_qty=Decimal("0.000"),
                )
                stock.recompute_closing()
                warnings.append(
                    f"\'{product.product_name}\': original stock row not found; "
                    "re-created with returned quantity."
                )

            # Reduce ProductStock aggregate
            ps_qs = ProductStock.objects.select_for_update().filter(
                product=product,
                location_type=out_entry.location_type,
                location_id=out_entry.location_id,
            )
            if ps_qs.exists():
                ps = ps_qs.first()
                ps.total_out_qty = max(
                    Decimal("0.000"),
                    (ps.total_out_qty or Decimal("0")) - return_qty,
                )
                ps.save(update_fields=["total_out_qty", "updated_at"])

            StockLedger.objects.create(
                product=product,
                batch=batch,
                location_type=out_entry.location_type,
                location_id=out_entry.location_id,
                transaction_type="SERVICE_RETURN",
                transaction_ref=out_entry.transaction_ref,
                document_id=service.id,
                in_qty=return_qty,
                out_qty=Decimal("0.000"),
                balance_qty=stock.closing_qty,
                created_by=user,
                remarks=(
                    f"Partial return service #{service.id} — "
                    f"{product.product_name} x{return_qty} returned to available stock"
                ),
            )

    return warnings, errors




def get_service_sub_item_stock_out_summary(service):
    """
    Returns a list of dicts for sub-items linked to a service.
    Used to pre-fill the partial-return form.

    Reads directly from ServiceProductItem records so this works for services
    approved before sub-item ledger tracking was added.

    Each dict:
      {
        'spi_id'        : int   (ServiceProductItem PK - used as form key),
        'item_name'     : str,
        'parent_product': str,
        'out_qty'       : Decimal  (quantity used in the service),
        'returned'      : Decimal  (already returned via SERVICE_RETURN ledger),
        'returnable'    : Decimal,
        'location_type' : str,
        'location_id'   : int,
      }
    """
    from .models import StockLedger

    location_type, location_id = _get_service_location(service)

    rows = []
    for sp in service.service_products.select_related('product').prefetch_related(
        'selected_items__required_item'
    ).all():
        for spi in sp.selected_items.all():
            ri      = spi.required_item
            ref     = _sub_item_ref(service.id, ri.id)
            out_qty = Decimal(str(spi.quantity))

            already_returned = (
                StockLedger.objects.filter(
                    transaction_ref=ref,
                    transaction_type="SERVICE_RETURN",
                ).aggregate(total=Sum("in_qty"))["total"]
                or Decimal("0.000")
            )

            returnable = max(Decimal("0.000"), out_qty - already_returned)

            rows.append({
                "spi_id"        : spi.id,
                "item_name"     : ri.item_name,
                "parent_product": sp.product.product_name,
                "out_qty"       : out_qty,
                "returned"      : already_returned,
                "returnable"    : returnable,
                "location_type" : location_type,
                "location_id"   : location_id,
            })
    return rows
