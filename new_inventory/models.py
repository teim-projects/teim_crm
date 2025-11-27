from django.db import models
from crmapp.models import Product
from django.contrib.auth.models import User
from decimal import Decimal , ROUND_HALF_UP
import datetime
import random
from .utils import get_or_create_product_batch, get_destination_object
from django.db import transaction


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
    compony_type = models.CharField(max_length=100, blank=True, null=True)
    supplier_category = models.CharField(max_length=100, blank=True, null=True)
    gst_details = models.CharField(max_length=100, blank=True, null=True)

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
    gst_type = models.TextField(max_length=200, choices= (
        ('cgst_sgst', 'CGST SGST'),
        ('igst', 'IGST'),
    ))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_amount(self):
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.total

        freight = self.freight_charges or Decimal("0.00")
        return total + freight
    
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

    rate = models.DecimalField(max_digits=12, decimal_places=2, default=0 ,  blank=True, null=True)      # NEW
    gst_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0 ,  blank=True, null=True) 
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0, blank=True, null=True)   # NEW (%)

    remarks = models.TextField(null=True, blank=True)

    @property
    def total(self) -> Decimal:
        """
        Final item total = (qty * rate - discount%) + GST%.
        """
        qty = self.quantity or Decimal("0")
        rate = self.rate or Decimal("0")
        disc = self.discount or Decimal("0")
        gst = self.gst_rate or Decimal("0")

        base = qty * rate
        discount_amount = base * (disc / Decimal("100"))
        after_discount = base - discount_amount
        gst_amount = after_discount * (gst / Decimal("100"))

        return (after_discount + gst_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def __str__(self):
        return f"{self.product} ({self.quantity})"


# ----------------------------- GRN ------------------------------
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
                if self.batch is None and self.product_id:
                    # Prefer to use GRN's batch (one batch for whole GRN)
                    grn_batch = None
                    if self.grn_id:
                        # If the parent GRN exists and has a batch, use it
                        grn = GoodsReceiveNote.objects.select_for_update().filter(id=self.grn_id).first()
                        if grn and grn.batch:
                            grn_batch = grn.batch

                    # Allow overriding: if caller set _batch_no_str we use utils to find/create with that batch_no,
                    # otherwise use the GRN-created Batch
                    batch_no_str = getattr(self, "_batch_no_str", None)

                    product_batch = get_or_create_product_batch(
                        product=self.product,
                        batch=grn_batch,
                        batch_no_str=batch_no_str,
                        manufacturing_date=getattr(self, "_manufacturing_date", None),
                        expiry_date=getattr(self, "_expiry_date", None),
                    )
                    self.batch = product_batch

                if self.ordered_qty is not None and self.received_qty is not None:
                    rem = Decimal(self.ordered_qty) - Decimal(self.received_qty)
                    self.remaining_qty = rem if rem >= 0 else Decimal("0.00")

                super().save(*args, **kwargs)

        except Exception:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Error saving GoodsReceiveNoteItem (auto-batch creation)")
            raise

        def __str__(self):
            return f"GRN Item - {getattr(self.product, 'product_name', str(self.product))}"
