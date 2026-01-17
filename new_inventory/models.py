from venv import logger
from django.db import models
from crmapp.models import Product
from django.contrib.auth.models import User
from decimal import Decimal , ROUND_HALF_UP
import datetime
import random
from .utils import get_or_create_product_batch, get_destination_object
from django.db import transaction
from django.utils import timezone
import logging
from django.core.exceptions import ValidationError

# ----------------------------- CONSTANTS ------------------------------

LOCATION_TYPES = (
    ("BRANCH", "Branch"),
    ("HO", "Head Office"),
    ("SITE", "Site"),
)

DESTINATION_TYPES = LOCATION_TYPES

STATUS_CHOICES = (
    ("DRAFT", "Draft"),
    ("APPROVED", "Approved"),
    ("PARTIALLY_RECEIVED", "Partially Received"),
    ("CLOSED", "Closed"),
)

TRANSACTION_TYPES = (
    ("GRN_IN", "GRN In"),
    ("MTN_OUT", "Material Transfer Out"),
    ("MTN_IN", "Material Transfer In"),
    ("ADJUST", "Stock Adjustment"),
)



# ----------------------------- BATCH ------------------------------

def generate_batch_no():
    today = datetime.date.today()
    base = f"BATCH-{today.strftime('%d-%m-%y')}"
    batch_no = base

    while Batch.objects.filter(batch_no=batch_no).exists():
        random_no = random.randint(100, 999)
        batch_no = f"{base}/{random_no}"

    return batch_no


class Batch(models.Model):
    batch_no = models.CharField(
        max_length=255,
        unique=True,
        default=generate_batch_no,
        editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.batch_no


# ----------------------------- VENDOR ------------------------------

class Vendor(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, blank=True, null=True)
    mobile = models.CharField(max_length=15)
    website = models.URLField(blank=True, null=True)
    bank_details = models.TextField(blank=True, null=True)
    office_address = models.TextField(blank=True, null=True)
    store_address = models.TextField(blank=True, null=True)
    company_type = models.CharField(max_length=100, blank=True, null=True)
    supplier_category = models.CharField(max_length=100, blank=True, null=True)
    gst_details = models.CharField(max_length=100, blank=True, null=True)
    # pan_no = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    state_code = models.CharField(max_length=100, blank=True, null=True)

    office_poc_name = models.CharField(max_length=100, blank=True, null=True)
    office_poc_phone = models.CharField(max_length=15, blank=True, null=True)

    store_poc_name = models.CharField(max_length=100, blank=True, null=True)
    store_poc_phone = models.CharField(max_length=15, blank=True, null=True)
    pan_details = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=200, blank=True, null=True)
    code = models.CharField(max_length=200, blank=True, null=True)
    def __str__(self):
        return f"{self.name} - {self.mobile}"


# ----------------------------- PRODUCT BATCH ------------------------------

class ProductBatch(models.Model):
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT,
        related_name="product_batches",
        blank=True, null=True
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE,
        related_name="batches"
    )
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "batch")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.product.product_name} - {self.batch}"


# ----------------------------- HO STAFF ------------------------------

class HO(models.Model):
    ROLE_CHOICES = (
        ('HO_manager', 'HO Manager'),
        ('HO_operation', 'HO Operation'),
    )

    user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='ho')
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=50, blank=True, null=True)
    contact = models.CharField(max_length=255, null=True, blank=True, unique=True)
    address = models.TextField(null=True, blank=True)
    role = models.CharField(max_length=100, choices=ROLE_CHOICES)

    def __str__(self):
        return self.name


# ----------------------------- SITE ------------------------------

class Site(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


# ----------------------------- PURCHASE ORDER ------------------------------

def generate_po_no():
    current_year = datetime.date.today().year
    prefix = f"PO_{current_year}"

    last_po = PurchaseOrder.objects.filter(po_no__startswith=prefix).order_by("-po_no").first()
    if last_po:
        last_number = int(last_po.po_no[-3:])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:03d}"


class PurchaseOrder(models.Model):
    po_no = models.CharField(
        max_length=255,
        unique=True,
        default=generate_po_no,
        editable=False
    )

    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True)

    destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPES)
    destination_id = models.BigIntegerField()

    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="DRAFT")
    material_supply = models.TextField(null=True, blank=True)

    quotation_attachment = models.FileField(max_length=500, null=True, blank=True)

    freight_charges = models.DecimalField(     # NEW FIELD
        max_digits=12, decimal_places=2, default=0
    )

    mode_terms_of_payments = models.TextField(blank=True, null=True)
    terms_of_delivery = models.TextField(blank=True, null=True)
    gst_type = models.CharField(
        max_length=20,
        choices=(
            ('no_gst', 'No GST'),
            ('cgst_sgst', 'CGST+SGST'),
            ('igst', 'IGST'),
        ),
        default='no_gst'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_gst(self) -> Decimal:
        """Sum of gst_amount across all items (Decimal)"""
        total = Decimal("0.00")
        for item in self.items.all():
            total += (item.gst_amount or Decimal("0.00"))
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


    @property
    def cgst_total(self) -> Decimal:
        """Half of total_gst when gst_type is cgst_sgst, else 0"""
        if (self.gst_type or "").lower() == "cgst_sgst":
            return (self.total_gst / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Decimal("0.00")


    @property
    def sgst_total(self) -> Decimal:
        """Half of total_gst when gst_type is cgst_sgst, else 0"""
        if (self.gst_type or "").lower() == "cgst_sgst":
            return (self.total_gst / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return Decimal("0.00")


    @property
    def igst_total(self) -> Decimal:
        """All GST as IGST only when gst_type is igst"""
        if (self.gst_type or "").lower() == "igst":
            return self.total_gst
        return Decimal("0.00")


    @property
    def is_no_gst(self):
        return (self.gst_type or "").lower() == "no_gst"


    @property
    def grand_total(self) -> Decimal:
        """
        Grand total = sum(item.amount_excl_gst) + total_gst + freight
        (keeps numbers consistent with separate gst fields)
        """
        subtotal = Decimal("0.00")
        for item in self.items.all():
            subtotal += (item.amount_excl_gst or Decimal("0.00"))

        freight = self.freight_charges or Decimal("0.00")
        total = subtotal + self.total_gst + freight
        return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self):
        return self.po_no

# ----------------------------- PURCHASE ORDER ITEMS ------------------------------
class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(
        PurchaseOrder, on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)

    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.CharField(max_length=200, blank=True, null=True)
    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    gst_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0, blank=True, null=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, null=True)

    description = models.TextField(null=True, blank=True)   # 👈 NEW
    remarks = models.TextField(null=True, blank=True)


    @property
    def amount_excl_gst(self) -> Decimal:
        """
        Base amount after discount, BEFORE GST.
        (This mirrors the logic used inside your current total calculation.)
        """
        qty = self.quantity or Decimal("0")
        rate = self.rate or Decimal("0")
        disc = self.discount or Decimal("0")

        base = qty * rate
        discount_amount = (base * (disc / Decimal("100")))
        after_discount = base - discount_amount

        return after_discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @property
    def gst_amount(self) -> Decimal:
        """
        GST amount for this item (computed on after-discount amount).
        """
        after_discount = self.amount_excl_gst
        gst = self.gst_rate or Decimal("0")
        gst_amt = (after_discount * (gst / Decimal("100"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return gst_amt

    @property
    def total(self) -> Decimal:
        """
        If you want total to include GST, return after_discount + gst_amount.
        If you prefer total to remain amount BEFORE GST, keep original behaviour.
        Below I return amount BEFORE GST to match your current code.
        """
        return self.amount_excl_gst

    def __str__(self):
        return f"{self.product} ({self.quantity})"


# ----------------------------- GRN ------------------------------

def generate_grn_no_per_po(purchase_order):
    """
    purchase_order: instance of PurchaseOrder
    """
    po_no = purchase_order.po_no  # adjust if field name differs
    safe_po = po_no.replace(" ", "").replace("/", "-")
    prefix = f"GRN_{safe_po}_"

    last = GoodsReceiveNote.objects.filter(
        grn_no__startswith=prefix,
        purchase_order=purchase_order
    ).order_by("-grn_no").first()

    if last and last.grn_no:
        try:
            last_seq = int(last.grn_no.split("_")[-1])   # expects suffix like 001
        except Exception:
            last_seq = 0
        new_seq = last_seq + 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:03d}"


class GoodsReceiveNote(models.Model):
    grn_no = models.CharField(max_length=60, unique=True, blank=True)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    destination_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    destination_id = models.BigIntegerField()
    received_date = models.DateField()
    remarks = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="DRAFT")

    # ------------------ new field ------------------
    batch = models.ForeignKey(
        Batch, on_delete=models.PROTECT, null=True, blank=True,
        related_name="grns"
    )
    # ------------------------------------------------

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # ensure grn_no
        if not self.grn_no:
            if self.purchase_order_id:
                self.grn_no = generate_grn_no_per_po(self.purchase_order)

        # ensure a Batch exists for this GRN (if not set by view)
        if not self.batch:
            # create a readable default batch name (e.g. "BATCH-nov-25")
            self.batch = Batch.objects.create()

        super().save(*args, **kwargs)

    @property
    def destination_name(self):
        obj = get_destination_object(self.destination_type, self.destination_id)
        return str(obj) if obj else "N/A"

    def __str__(self):
        return f"GRN-{self.grn_no}"

logger = logging.getLogger(__name__)

class GoodsReceiveNoteItem(models.Model):
    grn = models.ForeignKey(GoodsReceiveNote, on_delete=models.CASCADE, related_name="items")
    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="grn_items")
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT, null=True, blank=True)
    ordered_qty = models.DecimalField(max_digits=12, decimal_places=2)
    received_qty = models.DecimalField(max_digits=12, decimal_places=2)
    remaining_qty = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    remarks = models.CharField(max_length=255, null=True, blank=True)

    

    def save(self, *args, **kwargs):
        try:
            with transaction.atomic():
                # --- existing batch auto-creation logic (unchanged) ---
                if self.batch is None and self.product_id:
                    grn_batch = None
                    if self.grn_id:
                        grn = GoodsReceiveNote.objects.select_for_update().filter(id=self.grn_id).first()
                        if grn and grn.batch:
                            grn_batch = grn.batch

                    batch_no_str = getattr(self, "_batch_no_str", None)

                    product_batch = get_or_create_product_batch(
                        product=self.product,
                        batch=grn_batch,
                        batch_no_str=batch_no_str,
                        manufacturing_date=getattr(self, "_manufacturing_date", None),
                        expiry_date=getattr(self, "_expiry_date", None),
                    )
                    self.batch = product_batch

                # --- compute remaining correctly when po_item is set ---
                if self.po_item_id:
                    # Lock the PO item row to reduce race conditions
                    poi = PurchaseOrderItem.objects.select_for_update().get(id=self.po_item_id)

                    # Try to find the ordered quantity field on the PO item (robust fallback)
                    possible_names = ("ordered_qty", "order_qty", "qty", "quantity", "po_qty")
                    ordered_qty_value = None
                    for name in possible_names:
                        if hasattr(poi, name):
                            val = getattr(poi, name)
                            # accept numeric-like values (Decimal, int, str that can be Decimal)
                            try:
                                ordered_qty_value = Decimal(val)
                            except Exception:
                                ordered_qty_value = None
                            break

                    # fallback to this GRN item's ordered_qty if present
                    if ordered_qty_value is None and getattr(self, "ordered_qty", None) is not None:
                        try:
                            ordered_qty_value = Decimal(self.ordered_qty)
                        except Exception:
                            ordered_qty_value = None

                    if ordered_qty_value is None:
                        # We couldn't find an ordered quantity to compute against.
                        # Log and fall back to per-line calculation (so we don't crash).
                        logger.warning(
                            "Could not determine ordered quantity for PO item id %s; "
                            "falling back to line-level ordered_qty if available.",
                            self.po_item_id
                        )
                        if self.ordered_qty is not None and self.received_qty is not None:
                            rem = Decimal(self.ordered_qty) - Decimal(self.received_qty)
                            self.remaining_qty = rem if rem >= 0 else Decimal("0.00")
                        else:
                            # leave as is (or set zero)
                            self.remaining_qty = Decimal("0.00")
                    else:
                        # Sum of other GRN items' received_qty for this PO item (exclude this if updating)
                        qs = GoodsReceiveNoteItem.objects.filter(po_item_id=self.po_item_id)
                        if self.pk:
                            qs = qs.exclude(pk=self.pk)
                        other_total = qs.aggregate(total=models.Sum('received_qty'))['total'] or Decimal('0.00')

                        this_received = Decimal(self.received_qty or 0)
                        cumulative = Decimal(other_total) + this_received

                        rem = ordered_qty_value - cumulative
                        self.remaining_qty = rem if rem >= 0 else Decimal('0.00')
                else:
                    # fallback: use the line's ordered/received fields
                    if self.ordered_qty is not None and self.received_qty is not None:
                        rem = Decimal(self.ordered_qty) - Decimal(self.received_qty)
                        self.remaining_qty = rem if rem >= 0 else Decimal("0.00")

                # finally persist
                super().save(*args, **kwargs)

        except Exception:
            logger.exception("Error saving GoodsReceiveNoteItem (auto-batch creation)")
            raise
    def __str__(self):
        return f"GRN Item - {getattr(self.product, 'product_name', str(self.product))}"



# ------------------ MTN ---------------
def generate_mtn_no():
    current_year = datetime.date.today().year
    prefix = f"MTN/{current_year}/"

    # Find the last MTN created in the current year
    last_mtn = MaterialTransferNote.objects.filter(
        mtn_no__startswith=prefix
    ).order_by("-mtn_no").first()

    if last_mtn:
        # Extracts the last 3 digits, e.g., '005' -> 5
        try:
            last_number = int(last_mtn.mtn_no.split('/')[-1])
            new_number = last_number + 1
        except (ValueError, IndexError):
            new_number = 1
    else:
        new_number = 1

    return f"{prefix}{new_number:03d}"


# ----------------------------- MATERIAL TRANSFER ------------------------------

class MaterialTransferNote(models.Model):
    mtn_no = models.CharField(
        max_length=100, 
        unique=True, 
        default=generate_mtn_no, 
        editable=False           
    )
    
    # Source Location
    source_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    source_id = models.BigIntegerField()
    
    # Destination Location
    destination_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    destination_id = models.BigIntegerField()
    
    transfer_date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="DRAFT")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    remark = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.mtn_no:
            # Simple auto-gen logic; can be customized like your PO/GRN logic
            date_str = timezone.now().strftime('%Y%m%d')
            last_mtn = MaterialTransferNote.objects.filter(mtn_no__contains=date_str).count()
            self.mtn_no = f"MTN-{date_str}-{last_mtn + 1:03d}"
        super().save(*args, **kwargs)


    @property
    def source_name(self):
        obj = get_destination_object(self.source_type, self.source_id)
        return str(obj) if obj else "N/A"

    @property
    def destination_name(self):
        obj = get_destination_object(self.destination_type, self.destination_id)
        return str(obj) if obj else "N/A"
    def __str__(self):
        return self.mtn_no

class MTNItem(models.Model):
    mtn = models.ForeignKey(MaterialTransferNote, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT)
    transfer_qty = models.DecimalField(max_digits=12, decimal_places=3)
    remarks = models.CharField(max_length=255, null=True, blank=True)


    def clean(self):
        # Only validate during creation or if it's still a draft
        if self.mtn.status == 'DRAFT':
            stock = CurrentStock.objects.filter(
                product=self.product,
                batch=self.batch,
                location_type=self.mtn.source_type,
                location_id=self.mtn.source_id
            ).first()

            # available_qty = closing_qty - reserved_qty
            available = stock.available_qty if stock else Decimal('0')

            # If updating, we need to ignore the current item's already reserved amount
            if self.pk:
                old_item = MTNItem.objects.get(pk=self.pk)
                available += old_item.transfer_qty

            if self.transfer_qty > available:
                raise ValidationError(
                    f"Insufficient stock at source. Available: {available}."
                )
    
    def save(self, *args, **kwargs):
        # 🔑 Force Decimal conversion (safe)
        if self.transfer_qty is not None:
            self.transfer_qty = Decimal(self.transfer_qty)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_name} - {self.transfer_qty}"






# ------------ current stock -----------------------
class CurrentStock(models.Model):
    product = models.ForeignKey('crmapp.Product', on_delete=models.CASCADE)
    batch = models.ForeignKey('ProductBatch', on_delete=models.PROTECT, null=True, blank=True)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    location_id = models.BigIntegerField()
    opening_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    in_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))   # cumulative in
    out_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))  # cumulative out
    reserved_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    closing_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'batch', 'location_type', 'location_id')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['batch']),
            models.Index(fields=['location_type', 'location_id']),
        ]
    
    @property
    def available_qty(self):
        """Quantity actually available for use (closing - reserved)."""
        return (self.closing_qty or Decimal('0')) - (self.reserved_qty or Decimal('0'))

    def recompute_closing(self):
        """Recompute and save closing based on opening/in/out/reserved."""
        self.closing_qty = (self.opening_qty or Decimal('0')) + (self.in_qty or Decimal('0')) - (self.out_qty or Decimal('0')) - (self.reserved_qty or Decimal('0'))
        self.save(update_fields=['closing_qty', 'last_updated'])

    def __str__(self):
        return f"{self.product} / {self.batch or 'NO-BATCH'} @ {self.location_type}:{self.location_id} -> {self.closing_qty}"

# -------------- stock ledger ----------------------
class StockLedger(models.Model):
    product = models.ForeignKey('crmapp.Product', on_delete=models.CASCADE)
    batch = models.ForeignKey('ProductBatch', on_delete=models.PROTECT, null=True, blank=True)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    location_id = models.BigIntegerField()
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    transaction_ref = models.CharField(max_length=255, null=True, blank=True)  # used to link to GRN item e.g. GRN_ITEM_12
    document_id = models.BigIntegerField(null=True, blank=True)  # e.g. GRN id
    in_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    out_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    balance_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    transaction_date = models.DateField(default=timezone.now)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['transaction_date'])
        ]

    def __str__(self):
        return f"{self.transaction_type} {self.product} +{self.in_qty} -{self.out_qty} -> bal {self.balance_qty} ({self.transaction_ref})"
    
#  ------------- product stock --------------------
class ProductStock(models.Model):
    """
    Denormalized table for product-level stock per location.
    Updated by signals when GRN/MTN/DC events occur.
    """
    product = models.ForeignKey('crmapp.Product', on_delete=models.CASCADE)
    location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    location_id = models.BigIntegerField()

    # aggregated totals
    total_in_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    total_out_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))
    total_reserved_qty = models.DecimalField(max_digits=18, decimal_places=3, default=Decimal('0.000'))

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'location_type', 'location_id')
        indexes = [
            models.Index(fields=['product']),
            models.Index(fields=['location_type', 'location_id']),
        ]

    def __str__(self):
        return f"{self.product} @ {self.location_type}:{self.location_id} -> {self.closing_qty}"

    @property
    def closing_qty(self):
        return (self.total_in_qty or Decimal('0')) - (self.total_out_qty or Decimal('0')) - (self.total_reserved_qty or Decimal('0')) 
    


# Material Request Ho to Branch
class MaterialRequest(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    )

    request_no = models.CharField(max_length=50, unique=True)
    
    # branch raising request
    source_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPES,
        default="BRANCH"
    )
    source_id = models.BigIntegerField()  # branch.id

    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    request_date = models.DateField(default=timezone.now)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="DRAFT"
    )
    remarks = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    @property
    def source_name(self):
        from crmapp.models import Branch
        if self.source_type == "BRANCH":
            branch = Branch.objects.filter(id=self.source_id).first()
            return str(branch) if branch else "N/A"
        return "N/A"

    def __str__(self):
        return self.request_no


class MaterialRequestItem(models.Model):
    material_request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    requested_qty = models.DecimalField(max_digits=12, decimal_places=3)
    approved_qty = models.DecimalField(
        max_digits=12, decimal_places=3,
        null=True, blank=True
    )

    remarks = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.requested_qty}"



class Notification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    related_request = models.ForeignKey(
        MaterialRequest,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"
    

    #-----------------------challan--------------------


# ---------------- DELIVERY CHALLAN ----------------

def generate_dc_no():
    today = timezone.now().strftime("%Y%m%d")
    prefix = f"DC/{today}/"
    last = DeliveryChallan.objects.filter(
        dc_no__startswith=prefix
    ).order_by("-dc_no").first()

    if last:
        last_no = int(last.dc_no.split("/")[-1])
        new_no = last_no + 1
    else:
        new_no = 1

    return f"{prefix}{new_no:03d}"


class DeliveryChallan(models.Model):
    dc_no = models.CharField(
        max_length=50,
        unique=True,
        default=generate_dc_no,
        editable=False
    )

    # 🔗 LINK TO MTN
    mtn = models.OneToOneField(
        MaterialTransferNote,
        on_delete=models.PROTECT,
        related_name="delivery_challan"
    )

    source_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    source_id = models.BigIntegerField()

    destination_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    destination_id = models.BigIntegerField()

    delivery_date = models.DateField(default=timezone.now)

    status = models.CharField(
        max_length=20,
        choices=(
            ("DRAFT", "Draft"),
            ("DISPATCHED", "Dispatched"),
        ),
        default="DRAFT"
    )

    remarks = models.TextField(null=True, blank=True)

    # ✅ ADD ONLY THESE 3 FIELDS
    delivery_partner_name = models.CharField(
        max_length=100, blank=True, null=True
    )
    delivery_person_name = models.CharField(
        max_length=100, blank=True, null=True
    )
    delivery_person_phone = models.CharField(
        max_length=15, blank=True, null=True
    )

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.dc_no



class DeliveryChallanItem(models.Model):
    delivery_challan = models.ForeignKey(
        DeliveryChallan,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    batch = models.ForeignKey(ProductBatch, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    remarks = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"{self.product} - {self.quantity}"
