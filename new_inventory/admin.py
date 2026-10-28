from django.contrib import admin
from django.db import transaction
from .models import (
    Vendor, Batch, ProductBatch, Site, HO, 
    GoodsReceiveNote, GoodsReceiveNoteItem, CurrentStock, 
    MaterialTransferNote, MTNItem, StockLedger , ProductStock
)
from crmapp.models import Product

# --- BASIC REGISTRATIONS ---
admin.site.register(Vendor)
admin.site.register(Site)
admin.site.register(HO)
admin.site.register(StockLedger)
admin.site.register(ProductStock)

# --- PRODUCT REGISTRATION (with Autocomplete support) ---
if admin.site.is_registered(Product):
    admin.site.unregister(Product)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    search_fields = ['product_name', 'product_id']
    list_display = ('product_name', 'product_id')

# --- BATCH REGISTRATION ---
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("batch_no", "created_at")
    search_fields = ("batch_no",) # Required for ProductBatch autocomplete

# --- PRODUCT BATCH REGISTRATION ---
@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("product", "get_batch_no", "manufacturing_date", "expiry_date")
    list_filter = ("product",)
    search_fields = ['batch__batch_no', 'product__product_name'] # Required for MTN autocomplete

    @admin.display(description='Batch No')
    def get_batch_no(self, obj):
        return obj.batch.batch_no if obj.batch else "No Batch"

# --- STOCK REGISTRATION ---
@admin.register(CurrentStock)
class CurrentStockAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'batch', 'location_type', 'location_id', 
        'closing_qty', 'available_qty', 'last_updated'
    )
    list_filter = ('location_type', 'product')

# --- GRN REGISTRATION ---
class GRNItemInline(admin.TabularInline):
    model = GoodsReceiveNoteItem
    extra = 1

@admin.register(GoodsReceiveNote)
class GoodsReceiveNoteAdmin(admin.ModelAdmin):
    list_display = ('grn_no', 'purchase_order', 'status', 'received_date')
    inlines = [GRNItemInline]

# --- MATERIAL TRANSFER NOTE (MTN) REGISTRATION ---
class MTNItemInline(admin.TabularInline):
    model = MTNItem
    extra = 1
    autocomplete_fields = ['product', 'batch'] # Now works because targets have search_fields

@admin.register(MaterialTransferNote)
class MaterialTransferNoteAdmin(admin.ModelAdmin):
    list_display = ('mtn_no', 'source_type', 'source_id', 'destination_type', 'destination_id', 'status')
    list_filter = ('status', 'source_type', 'destination_type')
    inlines = [MTNItemInline]
    readonly_fields = ('mtn_no',)
    actions = ['approve_mtn']

    @admin.action(description="Approve MTN and Move Stock")
    def approve_mtn(self, request, queryset):
        for mtn in queryset:
            if mtn.status == 'DRAFT':
                mtn.status = 'APPROVED'
                mtn.save() # This triggers the post_save signal in signals.py
                self.message_user(request, f"{mtn.mtn_no} approved successfully.")
            else:
                self.message_user(request, f"{mtn.mtn_no} is already {mtn.status}.", level='warning')



