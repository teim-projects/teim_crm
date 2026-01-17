from django.contrib import admin
from django.utils import timezone

from .models import (
    AMCContract,
    AMCServiceSchedule,
    AMCServiceVisit,
)


# ---------------------------------
# AMC CONTRACT ADMIN
# ---------------------------------
@admin.register(AMCContract)
class AMCContractAdmin(admin.ModelAdmin):

    list_display = (
        "contract_number",
        "customer",
        "start_date",
        "end_date",
        "frequency",
        "status",
        "is_active",
    )

    list_filter = (
        "status",
        "is_active",
        "amc_type",
        "branch",
    )

    search_fields = (
        "contract_number",
        "customer__fullname",
    )

    readonly_fields = (
        "contract_number",
        "end_date",
        "created_at",
    )


# ---------------------------------
# AMC SERVICE SCHEDULE ADMIN
# ---------------------------------
@admin.register(AMCServiceSchedule)
class AMCServiceScheduleAdmin(admin.ModelAdmin):

    list_display = (
        "amc",
        "service_date",
        "is_completed",
        "reminder_sent",
    )

    list_filter = (
        "is_completed",
        "reminder_sent",
    )

    readonly_fields = ("service_date",)

    date_hierarchy = "service_date"
    ordering = ("service_date",)


# ---------------------------------
# AMC SERVICE VISIT ADMIN
# ---------------------------------
from django.contrib import admin
from django.utils import timezone
from .models import AMCServiceVisit
from crmapp.models import TechWorkList


@admin.register(AMCServiceVisit)
class AMCServiceVisitAdmin(admin.ModelAdmin):

    list_display = (
        "amc",
        "service_date",
        "crm_visit_status",
    )

    ordering = ("-service_date",)

    list_filter = ("amc",)

    filter_horizontal = ("technicians",)

    def crm_visit_status(self, obj):
        """
        Read-only completion status coming from CRM (TechWorkList)
        """
        if not obj.crm_service:
            return "Not Linked"

        completed = TechWorkList.objects.filter(
            service=obj.crm_service,
            status="Completed"
        ).exists()

        return "Completed" if completed else "Pending"

    crm_visit_status.short_description = "Visit Status (CRM)"
