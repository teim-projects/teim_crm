from django.db import models
from crmapp.models import Product
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
import datetime
import random

LOCATION_TYPES = (
    ("BRANCH", "Branch"),
    ("HO", "Head Office"),
    ("SITE", "Site"),
)

DESTINATION_TYPES = LOCATION_TYPES

TRANSACTION_TYPES = (
    ("GRN_IN", "GRN In"),
    ("MTN_OUT", "Material Transfer Out"),
    ("MTN_IN", "Material Transfer In"),
    ("ADJUST", "Stock Adjustment"),
)

# generate a unique batch number 
def generate_batch_no():
    today = datetime.date.today()
    base = f"BATCH-{today.strftime('%d-%m-%y')}"
    batch_no = base

    # If exists -> add random suffix
    while Batch.objects.filter(batch_no=batch_no).exists():
        random_no = random.randint(100,999)
        batch_no = f"{base}/{random_no}"
    
    return batch_no


class Batch(models.Model):
    batch_no = models.CharField(max_length=255,
                                unique=True,
                                default=generate_batch_no,
                                editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
    
    def __str__(self):
        return self.batch_no

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
  
  def __str__(self):
    return f"{self.name } - {self.mobile}"
  

class ProductBatch(models.Model):
    batch_no = models.ForeignKey(Batch, on_delete=models.SET_NULL, related_name="product_batches" , blank=True, null=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="batches")
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("product", "batch_no")
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.product.product_name} - {self.batch_no}"

  
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


class Site(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField(null=True, blank=True)
    contact_person = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name
    


def generate_po_no():
    current_year = datetime.date.today().year
    prefix = f"PO_{current_year}"

    # Find last PO of this year
    last_po = PurchaseOrder.objects.filter(po_no__startswith=prefix).order_by("-po_no").first()

    if last_po:
        # Extract last 3 digits
        last_number = int(last_po.po_no[-3:])
        new_number = last_number + 1
    else:
        new_number = 1

    return f"{prefix}{new_number:03d}"



STATUS_CHOICES = (
        ("DRAFT", "Draft"),
        ("APPROVED", "Approved"),
        ("PARTIALLY_RECEIVED", "Partially Received"),
        ("CLOSED", "Closed"),
    )

class PurchaseOrder(models.Model): 
    po_no = models.CharField(max_length=255, unique=True,default=generate_po_no,editable=False) 
    created_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True) 
    vendor = models.ForeignKey(Vendor, on_delete=models.SET_NULL, null=True) 
    destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPES)
    destination_id = models.BigIntegerField()
    status = models.CharField(max_length=50,choices=STATUS_CHOICES, default="DRAFT") 
    material_supply = models.TextField(null=True, blank=True) 
    quotation_attachment = models.FileField(max_length=500, null=True, blank=True) 
    created_at = models.DateTimeField(auto_now_add=True) 
    updated_at = models.DateTimeField(auto_now=True) 
    def __str__(self): 
        return self.po_no
    

class PurchaseOrderItem(models.Model): 
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items") 
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True) 
    quantity = models.DecimalField(max_digits=12, decimal_places=2)  
    remarks = models.TextField(null=True, blank=True)




#--------------------------------------------- GRN -------------------------------------------------

class GoodsReceiveNote(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE)
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE)

    received_location_type = models.CharField(max_length=20, choices=LOCATION_TYPES)
    received_location_id = models.BigIntegerField()

    received_date = models.DateField()
    invoice_no = models.CharField(max_length=255, null=True, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    remarks = models.TextField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"GRN-{self.id}"




class GoodsReceiveNoteItem(models.Model):
    grn = models.ForeignKey(GoodsReceiveNote, on_delete=models.CASCADE, related_name="items")
    po_item = models.ForeignKey(PurchaseOrderItem, on_delete=models.CASCADE)

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True)

    ordered_qty = models.DecimalField(max_digits=12, decimal_places=2)
    received_qty = models.DecimalField(max_digits=12, decimal_places=2)

    remarks = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"GRN Item - {self.product.product_name}"

