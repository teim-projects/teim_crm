from django.contrib import admin
from .models import PaymentsRecord
from .models import UserProfile
# Register your models here.

@admin.register(PaymentsRecord)
class PaymentsRecordAdmin(admin.ModelAdmin):
    list_display = [
        'payment_invoice_no',
        'main_invoice',
        'amount_paid',
        'amount_remaining',
        'payment_date',
        'ageing',  # 👈 This will now show in the list view
    ]

    readonly_fields = ['ageing']  

admin.site.register(UserProfile)