from django.db import models
from crmapp.models import Product
from django.contrib.auth.models import User
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