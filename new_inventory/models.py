from django.db import models

# Create your models here.
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
   

  
