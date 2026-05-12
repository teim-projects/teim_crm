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
    Returns (location_type, location_id) for stock deduction.

    All physical stock is held at HO. Services are done by branches, but
    chemicals/materials come from the central HO store.
    Always returns the HO location so deductions reflect reality.
    """
    from crmapp.models import Branch
    ho = Branch.objects.filter(is_head_office=True).first()
    if ho:
        return "HO", ho.id
    return "HO", 1


def deduct_stock_for_service(service, user):
    """
    Deducts inventory stock for every product linked to the service on approval.

    Strategy — FIFO across batches:
      - Gets all CurrentStock records for the product at the service location
      - Deducts from each batch in FIFO order (oldest batch first) until qty met
      - Updates ProductStock aggregate
      - Writes a StockLedger entry (SERVICE_OUT) per batch consumed

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
            .all()
        )

        if not service_products.exists():
            warnings.append("No products linked to this service — nothing to deduct.")
            return warnings

        for sp in service_products:
            product    = sp.product
            qty_needed = Decimal(str(sp.quantity))

            # ── 1. Find all CurrentStock rows for this product at this location ──
            # Order by id (FIFO — oldest batch entered first)
            stock_rows = CurrentStock.objects.select_for_update().filter(
                product=product,
                location_type=location_type,
                location_id=location_id,
            ).order_by('id')

            if not stock_rows.exists():
                warnings.append(
                    f"'{product.product_name}': No stock at {location_type} "
                    f"(id={location_id}). Deduction skipped."
                )
                continue

            # ── 2. Calculate total available across all batches ───────────────
            total_available = sum(cs.available_qty for cs in stock_rows)
            if total_available < qty_needed:
                warnings.append(
                    f"'{product.product_name}': Low stock — need {qty_needed}, "
                    f"total available {total_available}. Deducting what is available."
                )

            # ── 3. FIFO deduction across batches ─────────────────────────────
            remaining = qty_needed
            for stock in stock_rows:
                if remaining <= Decimal('0'):
                    break

                can_take = min(stock.available_qty, remaining)
                if can_take <= Decimal('0'):
                    continue

                stock.out_qty = (stock.out_qty or Decimal('0')) + can_take
                stock.recompute_closing()   # saves the record

                # ── 4. Write per-batch StockLedger entry ─────────────────────
                StockLedger.objects.create(
                    product=product,
                    batch=stock.batch,              # actual batch (not None)
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

            # ── 5. Update ProductStock aggregate (once per product) ───────────
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
            actually_deducted = qty_needed - remaining   # what we actually took
            ps.total_out_qty = (ps.total_out_qty or Decimal('0')) + actually_deducted
            ps.save(update_fields=['total_out_qty', 'updated_at'])

    return warnings


def reverse_stock_for_service(service, user):
    """
    Reverses stock deductions when a service is rejected / un-approved.

    Finds the SERVICE_OUT ledger entries for this service and adds the
    stock back to the same batch/location it was taken from.

    Returns:
        list[str] — warning messages
    """
    from .models import CurrentStock, ProductStock, StockLedger

    warnings = []
    location_type, location_id = _get_service_location(service)

    with transaction.atomic():
        # Find every SERVICE_OUT ledger entry for this service
        ledger_entries = StockLedger.objects.select_for_update().filter(
            transaction_ref=f"SERVICE_{service.id}",
            transaction_type="SERVICE_OUT",
        )

        if not ledger_entries.exists():
            warnings.append(
                f"No SERVICE_OUT ledger entries found for service #{service.id}. "
                "Nothing to reverse."
            )
            return warnings

        for entry in ledger_entries:
            qty_to_return = entry.out_qty
            product       = entry.product

            # ── 1. Find the exact CurrentStock row (same batch + location) ────
            stock_qs = CurrentStock.objects.select_for_update().filter(
                product=product,
                batch=entry.batch,              # same batch we deducted from
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
            else:
                warnings.append(
                    f"'{product.product_name}': Original stock record not found "
                    f"(batch={entry.batch}). Reversal skipped for this batch."
                )
                continue

            # ── 2. Update ProductStock aggregate ──────────────────────────────
            ps_qs = ProductStock.objects.select_for_update().filter(
                product=product,
                location_type=location_type,
                location_id=location_id,
            )
            if ps_qs.exists():
                ps = ps_qs.first()
                ps.total_out_qty = max(
                    Decimal('0.000'),
                    (ps.total_out_qty or Decimal('0')) - qty_to_return
                )
                ps.save(update_fields=['total_out_qty', 'updated_at'])

            # ── 3. Write reversal ledger entry ────────────────────────────────
            StockLedger.objects.create(
                product=product,
                batch=entry.batch,
                location_type=entry.location_type,
                location_id=entry.location_id,
                transaction_type="SERVICE_REVERSAL",
                transaction_ref=f"SERVICE_{service.id}",
                document_id=service.id,
                in_qty=qty_to_return,       # stock coming back IN
                out_qty=Decimal('0.000'),
                balance_qty=stock.closing_qty,
                created_by=user,
                remarks=(
                    f"Reversal for service #{service.id} rejection — "
                    f"{product.product_name} x{qty_to_return} returned"
                ),
            )


    return warnings,


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
    Returns a SUBSET of stock that was deducted for a service back to inventory.

    Called after a service is completed and the technician returns unused materials.

    Args:
        service     : ServiceManagement instance
        return_items: list of dicts:
                        [{ 'ledger_id': int, 'return_qty': Decimal }, ...]
        user        : User instance (who is performing the return)

    Returns:
        (list[str] warnings, list[str] errors)
    """
    from .models import CurrentStock, ProductStock, StockLedger

    warnings = []
    errors   = []
    location_type, location_id = _get_service_location(service)

    with transaction.atomic():
        for item in return_items:
            ledger_id  = item.get("ledger_id")
            return_qty = Decimal(str(item.get("return_qty", 0)))

            if return_qty <= Decimal("0"):
                continue  # skip zero-qty rows silently

            # ── 1. Load the original SERVICE_OUT ledger entry ─────────────
            try:
                out_entry = StockLedger.objects.select_for_update().get(
                    pk=ledger_id,
                    transaction_ref=f"SERVICE_{service.id}",
                    transaction_type="SERVICE_OUT",
                )
            except StockLedger.DoesNotExist:
                errors.append(f"Ledger entry #{ledger_id} not found for this service.")
                continue

            product = out_entry.product
            batch   = out_entry.batch

            # ── 2. Guard: cannot return more than (deducted − already returned) ──
            already_returned = StockLedger.objects.filter(
                transaction_ref=f"SERVICE_{service.id}",
                transaction_type="SERVICE_RETURN",
                product=product,
                batch=batch,
            ).aggregate(total=Sum("in_qty"))["total"] or Decimal("0")

            max_returnable = out_entry.out_qty - already_returned
            if return_qty > max_returnable:
                warnings.append(
                    f"'{product.product_name}': return qty {return_qty} exceeds "
                    f"returnable {max_returnable}. Clamping to {max_returnable}."
                )
                return_qty = max_returnable

            if return_qty <= Decimal("0"):
                continue

            # ── 3. Add stock back to CurrentStock (same batch + location) ──
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
                # Stock row vanished — recreate with in_qty so it shows positive
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
                    f"'{product.product_name}': original stock row not found; "
                    "re-created with returned quantity."
                )

            # ── 4. Update ProductStock aggregate ──────────────────────────
            ps, _ = ProductStock.objects.select_for_update().get_or_create(
                product=product,
                location_type=location_type,
                location_id=location_id,
                defaults={
                    "total_in_qty"  : Decimal("0.000"),
                    "total_out_qty" : Decimal("0.000"),
                    "total_reserved_qty": Decimal("0.000"),
                },
            )
            ps.total_out_qty = max(
                Decimal("0.000"),
                (ps.total_out_qty or Decimal("0")) - return_qty,
            )
            ps.save(update_fields=["total_out_qty", "updated_at"])

            # ── 5. Write SERVICE_RETURN ledger entry ──────────────────────
            StockLedger.objects.create(
                product=product,
                batch=batch,
                location_type=out_entry.location_type,
                location_id=out_entry.location_id,
                transaction_type="SERVICE_RETURN",
                transaction_ref=f"SERVICE_{service.id}",
                document_id=service.id,
                in_qty=return_qty,
                out_qty=Decimal("0.000"),
                balance_qty=stock.closing_qty,
                created_by=user,
                remarks=(
                    f"Partial return after service #{service.id} — "
                    f"{product.product_name} x{return_qty} returned to inventory"
                ),
            )

    return warnings, errors
