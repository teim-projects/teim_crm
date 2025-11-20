from django.contrib import admin
from .models import Vendor , Batch, ProductBatch, Site, HO
# Register your models here.
admin.site.register(Vendor)
admin.site.register(Site)
admin.site.register(HO)
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("batch_no", "created_at")

@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("batch_no", "product", "manufacturing_date", "expiry_date")
    list_filter = ("batch_no", "product")
    