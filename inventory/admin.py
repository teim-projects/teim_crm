from django.contrib import admin
from .models import *
from crmapp.models import Product
# Register your models here.

admin.site.register(Product)
admin.site.register(ProductBatch)
admin.site.register(Vendor)
admin.site.register(purchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(GoodsReceiveNote)
admin.site.register(GoodsReceiveNoteItem)