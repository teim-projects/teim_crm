from django.contrib import admin
from .models import PaymentsRecord ,UserProfile, service_management, ServiceProduct, MessageTemplates

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

admin.site.register(service_management)
admin.site.register(ServiceProduct)


from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# Inline UserProfile inside User
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

# Custom User admin
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_role', 'get_phone')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'userprofile__role')  # 👈 custom filter

    def get_role(self, obj):
        return obj.userprofile.role
    get_role.short_description = 'Role'

    def get_phone(self, obj):
        return obj.userprofile.phone
    get_phone.short_description = 'Phone'

# Unregister the original User admin, then register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(MessageTemplates)