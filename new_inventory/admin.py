from django.contrib import admin
from .models import Vendor , Batch, ProductBatch, Site, HO, GoodsReceiveNote,GoodsReceiveNoteItem, CurrentStock
# Register your models here.
admin.site.register(Vendor)
admin.site.register(Site)
admin.site.register(HO)
admin.site.register(GoodsReceiveNote)
admin.site.register(GoodsReceiveNoteItem)
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("batch_no", "created_at")

@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("batch", "product", "manufacturing_date", "expiry_date")
    list_filter = ("batch", "product")
    
@admin.register(CurrentStock)
class CurrentStockAdmin(admin.ModelAdmin):
    list_display = ('id','product','batch','location_type','location_id','opening_qty','in_qty','out_qty','reserved_qty','closing_qty','available_qty','last_updated')