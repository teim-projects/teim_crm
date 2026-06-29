# amc/models.py

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import uuid

from crmapp.models import (
    customer_details,
    Branch,
    TechnicianProfile,
    service_management,
    Product,
    ServiceProductFrequency,
    WorkAllocation
)
from django.contrib.auth.models import User


# -----------------------------------------
# Helper: Contract number generator
# -----------------------------------------
def generate_contract_number():
    return f"AMC-{uuid.uuid4().hex[:8].upper()}"


# -----------------------------------------
# AMC CONTRACT
# -----------------------------------------
class AMCContract(models.Model):
    customer = models.ForeignKey(customer_details, on_delete=models.PROTECT)
    service = models.ForeignKey(service_management, on_delete=models.PROTECT)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)

    contract_number = models.CharField(
        max_length=50,
        unique=True,
        default=generate_contract_number,
        editable=False
    )

    amc_type = models.CharField(
        max_length=50,
        choices=[
            ("Comprehensive", "Comprehensive"),
            ("Non-Comprehensive", "Non-Comprehensive"),
            ("Warranty", "Warranty"),
        ],
        default="Comprehensive",
    )

    start_date = models.DateField()
    end_date = models.DateField(editable=False)

    # Deprecated – kept for backward compatibility
    frequency = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="(Deprecated) Use product-wise frequencies instead"
    )

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    per_visit_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    service_description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    # Default work details (used for all visits)
    default_customer_contact = models.CharField(max_length=15, blank=True, null=True)
    default_customer_address = models.TextField(blank=True, null=True)
    default_gps_location = models.URLField(blank=True, null=True)
    default_payment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    default_payment_status = models.CharField(
        max_length=20,
        choices=[("Pending", "Pending"), ("Cash", "Cash"), ("Online", "Online")],
        default="Pending"
    )
    default_work_description = models.TextField(blank=True, null=True)

    technicians = models.ManyToManyField(
        TechnicianProfile,
        blank=True,
        related_name="amc_contracts"
    )

    status = models.CharField(max_length=20, default="Active")
    is_active = models.BooleanField(default=True)

    # Renewal tracking
    RENEWAL_CHOICES = [
        ("PENDING", "Pending"),
        ("REQUESTED", "Requested"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("NOT_RENEWED", "Not Renewed"),
    ]
    renewal_status = models.CharField(
        max_length=20,
        choices=RENEWAL_CHOICES,
        default="PENDING"
    )
    renewal_requested_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ---------------------------------
    def clean_frequency(self):
        """Backward compatibility: normalise frequency input."""
        if not self.frequency:
            return None
        freq = self.frequency.strip().lower()
        if freq.isdigit():
            if int(freq) <= 0:
                raise ValidationError("Frequency must be greater than 0")
            return freq
        if freq not in ["weekly", "fortnight", "daily"]:
            raise ValidationError("Frequency must be 1–12, Weekly, Fortnight, or Daily")
        return freq

    def convert_freq_to_days_gap(self, freq_value):
        """Convert frequency string/number to days gap."""
        if freq_value is None:
            return None
        freq_str = str(freq_value).lower().strip()
        if freq_str.isdigit():
            freq_int = int(freq_str)
            if freq_int > 0:
                return max(1, round(365 / freq_int))
            return None
        if freq_str == "weekly":
            return 7
        if freq_str == "fortnight":
            return 14
        if freq_str == "daily":
            return 1
        return None

    # ---------------------------------
    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if self.frequency:
            self.frequency = self.clean_frequency()
        else:
            self.frequency = None

        if self.service:
            self.total_amount = (
                self.service.total_price_with_gst
                or self.service.total_price
                or self.service.total_charges
                or 0
            )

        if is_new:
            self.end_date = self.start_date
            self.per_visit_amount = 0
            if self.customer:
                self.default_customer_contact = self.customer.primarycontact
                self.default_customer_address = self.customer.shifttopartyaddress
            if self.service:
                self.default_gps_location = self.service.gps_location

        super().save(*args, **kwargs)

        if is_new:
            techs = set()
            for w in WorkAllocation.objects.filter(service=self.service):
                techs.update(w.technician.all())
            self.technicians.set(techs)
            self.generate_schedule()

    # ---------------------------------
    def generate_schedule(self):
        """
        Generate visits based on each product's frequency and duration_months.
        The AMC end_date becomes start_date + max(duration_months) across all products.
        """
        from amc.models import AMCServiceVisit, AMCServiceSchedule

        # Delete old schedules and visits
        AMCServiceVisit.objects.filter(amc=self).delete()
        AMCServiceSchedule.objects.filter(amc=self).delete()

        product_frequencies = ServiceProductFrequency.objects.filter(
            service=self.service
        )

        date_product_pairs = []
        max_duration_months = 0

        for pf in product_frequencies:
            freq = int(pf.frequency or 0)
            duration_months = int(getattr(pf, "duration_months", 12))
            max_duration_months = max(max_duration_months, duration_months)

            if freq <= 0:
                continue

            # Calculate gap in days based on frequency
            if freq == 365:
                gap_days = 1
            elif freq == 52:
                gap_days = 7
            elif freq == 26:
                gap_days = 15
            elif freq == 12:
                gap_days = 30
            elif freq == 6:
                gap_days = 60
            elif freq == 4:
                gap_days = 90
            elif freq == 2:
                gap_days = 180
            elif freq == 1:
                gap_days = 365
            else:
                gap_days = max(1, round(365 / freq))

            visit_date = self.start_date
            duration_days = duration_months * 30  # approximate

            while visit_date <= self.start_date + timedelta(days=duration_days):
                date_product_pairs.append({
                    "date": visit_date,
                    "product": pf.product
                })
                visit_date += timedelta(days=gap_days)

        # Fallback if no product frequencies exist
        if not date_product_pairs:
            for i in range(12):
                date_product_pairs.append({
                    "date": self.start_date + timedelta(days=i * 30),
                    "product": None
                })
            max_duration_months = 12

        # Sort by date
        date_product_pairs.sort(key=lambda x: x["date"])

        # Create schedules and visits
        for pair in date_product_pairs:
            service_date = pair["date"]
            product = pair["product"]

            AMCServiceSchedule.objects.get_or_create(
                amc=self,
                service_date=service_date
            )

            visit = AMCServiceVisit.objects.create(
                amc=self,
                service_date=service_date,
                product=product
            )
            visit.technicians.set(self.technicians.all())

        # Update AMC end_date and per-visit amount
        self.end_date = self.start_date + relativedelta(months=max_duration_months)
        total_visits = len(date_product_pairs)
        self.per_visit_amount = (
            self.total_amount / total_visits
            if total_visits > 0 else 0
        )
        self.default_payment_amount = self.per_visit_amount

        super().save(update_fields=[
            "end_date",
            "per_visit_amount",
            "default_payment_amount"
        ])

    # ---------------------------------
    @property
    def next_service_date(self):
        next_visit = self.visits.filter(
            service_date__gte=timezone.now().date()
        ).order_by("service_date").first()
        return next_visit.service_date if next_visit else None

    def __str__(self):
        return self.contract_number


# -----------------------------------------
# AMC SERVICE SCHEDULE (PLANNED)
# -----------------------------------------
class AMCServiceSchedule(models.Model):
    amc = models.ForeignKey(
        AMCContract,
        on_delete=models.CASCADE,
        related_name="service_schedules"
    )
    service_date = models.DateField()
    reminder_sent = models.BooleanField(default=False)
    is_completed = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.amc.contract_number} - {self.service_date}"


# -----------------------------------------
# SERVICE VISIT (ACTUAL)
# -----------------------------------------
class AMCServiceVisit(models.Model):
    amc = models.ForeignKey(
        AMCContract,
        on_delete=models.CASCADE,
        related_name="visits"
    )
    service_date = models.DateField()
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="amc_visits"
    )
    technicians = models.ManyToManyField(
        TechnicianProfile,
        blank=True,
        related_name="amc_visits"
    )
    crm_service = models.ForeignKey(
        service_management,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="amc_service_visits"
    )
    crm_service_created_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, null=True)

    allocation_status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("ALLOCATED", "Allocated"),
            ("CANCELLED", "Cancelled"),
        ],
        default="PENDING"
    )
    auto_allocation_done = models.BooleanField(default=False)
    allocation_cancelled_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def stop_future_visits_for_product(self):
        if not self.product:
            return
        # Cancel future pending visits for the same product
        AMCServiceVisit.objects.filter(
            amc=self.amc,
            product=self.product,
            service_date__gt=self.service_date,
            allocation_status="PENDING"
        ).update(
            allocation_status="CANCELLED",
            allocation_cancelled_reason="Auto stopped after product completion"
        )
        # Check if all visits are done
        pending = AMCServiceVisit.objects.filter(
            amc=self.amc,
            allocation_status="PENDING"
        ).exists()
        if not pending:
            self.amc.status = "COMPLETED"
            self.amc.is_active = False
            self.amc.save(update_fields=["status", "is_active"])

    def __str__(self):
        return f"{self.amc.contract_number} - {self.service_date} - {self.product}"