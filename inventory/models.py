from django.db import models
from django.db.models import Q, F, UniqueConstraint, CheckConstraint
from django.utils import timezone

from django.contrib.auth.models import User
from crmapp.models import Product


class ProductBatch(models.Model):
  product = models.ForeignKey(Product, on_delete=models.RESTRICT,related_name="batches")
  batch_no = models.CharField(max_length=200)
  manufacturing_date = models.DateField(null=True, blank=True)
  expiry_date = models.DateField(null=True, blank=True)

  class Meta:
    constraints = [
        UniqueConstraint(fields=["product", "batch_no"], name="uq_product_batch"),
        CheckConstraint(
            name="ck_batch_dates_order",
            check=Q(expiry_date__isnull=True) | Q(manufacturing_date__isnull=True) |
                  Q(expiry_date__gte=F("manufacturing_date")),
        ),
    ]
    indexes = [models.Index(fields=["product", "batch_no"])]

  def __str__(self):
    return f"{self.product} - {self.batch_no}"


class Vendor(models.Model):
  name = models.CharField(max_length=250)
  email = models.EmailField(blank=True, null=True)
  mobile = models.CharField(max_length=15, blank=True, null=True)
  website = models.URLField(blank=True, null=True)
  bank_details = models.TextField(blank=True, null=True)
  office_address = models.TextField(blank=True, null=True)
  store_address = models.TextField(blank=True, null=True)
  company_type = models.CharField(max_length=100, blank=True, null=True)
  supplier_category = models.CharField(max_length=100, blank=True, null=True)
  GST_details = models.CharField(max_length=50, blank=True, null=True)

  def __str__(self):
    return f"{self.name} - {self.mobile}"
  

class purchaseOrder(models.Model):
  user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="purchase_orders" )
  vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name="purchase_orders")
  status = models.CharField(max_length=100, default="draft")
  material_Supply = models.CharField(max_length=100, blank=True, null=True)
  quotation_attachment = models.FileField(upload_to="po/quotes/", blank=True, null=True)
  created_at = models.DateTimeField(auto_now_add=True)

  def __str__(self):
    return f"PO - {self.vendor}"


class PurchaseOrderItem(models.Model):
  po = models.ForeignKey(purchaseOrder, on_delete=models.CASCADE, related_name="items")
  product = models.ForeignKey(Product, on_delete=models.RESTRICT)
  quantity = models.DecimalField(max_digits=12, decimal_places=2)

  class Meta:
        constraints = [
            CheckConstraint(check=Q(quantity__gt=0), name="ck_poi_qty_gt0"),
        ]
        indexes = [models.Index(fields=["po"])]
  
  def __str__(self):
        return f"PO#{self.po_id} {self.product.product_name} x {self.quantity}"
  

class GoodsReceiveNote(models.Model):
   purchase_order = models.ForeignKey(purchaseOrder, on_delete=models.PROTECT, related_name='grns')
   recived_by = models.ForeignKey(User, on_delete=models.PROTECT,related_name='recived_grns')
   recived_date = models.DateField(default=timezone.now)
   status = models.CharField(max_length=100, default='received')
   remark = models.TextField(blank=True, null=True)
   created_at = models.DateTimeField(auto_now_add=True)

   def __str__(self):
        return f"GRN#{self.id} (PO#-{self.purchase_order.vendor})"

class GoodsReceiveNoteItem(models.Model):
   grn = models.ForeignKey(GoodsReceiveNote, on_delete=models.CASCADE, related_name='items')
   batch = models.ForeignKey(ProductBatch, on_delete=models.RESTRICT)
   ordered_qty = models.DecimalField(max_digits=13,decimal_places=3, default=0)
   received_qty = models.DecimalField(max_digits=13,decimal_places=3, default=0)
   remaining_qty = models.DecimalField(max_digits=13,decimal_places=3, default=0)
   remarks = models.CharField(max_length=255, blank=True, null=True)

   class Meta:
        constraints = [
            CheckConstraint(check=Q(received_qty__gte=0), name="ck_grni_recv_ge0"),
        ]
        indexes = [models.Index(fields=["grn"]), models.Index(fields=["batch"])]

   def __str__(self):
        return f"GRN#{self.grn_id} - {self.batch}"