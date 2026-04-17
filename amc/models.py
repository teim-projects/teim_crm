from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

from crmapp.models import (
    customer_details,
    Branch,
    TechnicianProfile,
    service_management
)


# ---------------------------------
# CONTRACT NUMBER GENERATOR

def generate_contract_number():
    year = timezone.now().year
    count = AMCContract.objects.count() + 1
    return f"AMC-{year}-{count:04d}"

# ---------------------------------
# AMC CONTRACT MODEL
# ---------------------------------
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

    frequency = models.CharField(
        max_length=20,
        help_text="1–12 OR Weekly / Fortnight / Daily"
    )

    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    per_visit_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    service_description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

        # ---------------------------------
    # AMC → DEFAULT WORK DETAILS (USED FOR ALL VISITS)
    # ---------------------------------
    default_customer_contact = models.CharField(
        max_length=15,
        blank=True,
        null=True
    )

    default_customer_address = models.TextField(
        blank=True,
        null=True
    )

    default_gps_location = models.URLField(
        blank=True,
        null=True
    )

    default_payment_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True
    )

    default_payment_status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Cash", "Cash"),
            ("Online", "Online"),
        ],
        default="Pending"
    )

    default_work_description = models.TextField(
        blank=True,
        null=True
    )


    technicians = models.ManyToManyField(
        TechnicianProfile,
        blank=True,
        related_name="amc_contracts"
    )

    status = models.CharField(max_length=20, default="Active")
    is_active = models.BooleanField(default=True)
        # ---------------------------------
    # AMC RENEWAL TRACKING
    # ---------------------------------
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

    renewal_requested_at = models.DateTimeField(
        null=True,
        blank=True
    )


    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # ---------------------------------
    def clean_frequency(self):
        freq = self.frequency.strip().lower()

        if freq.isdigit():
            if int(freq) <= 0:
                raise ValidationError("Frequency must be greater than 0")
            return freq

        if freq not in ["weekly", "fortnight", "daily"]:
            raise ValidationError(
                "Frequency must be 1–12, Weekly, Fortnight, or Daily"
            )

        return freq

    # ---------------------------------
    def save(self, *args, **kwargs):

        is_new = self.pk is None

        # normalize frequency
        self.frequency = self.clean_frequency()
        freq = self.frequency

        # total amount
        # total amount
        if self.service:
            self.total_amount = (
                self.service.total_price_with_gst
                or self.service.total_price
                or self.service.total_charges
                or 0
            )

        # ---------------------------------
        # TEMP VALUES FOR FIRST SAVE
        # ---------------------------------
        if is_new:
            self.end_date = self.start_date
            self.per_visit_amount = 0

            # AUTO-FILL DEFAULT WORK DATA FROM CRM
            if self.customer:
                self.default_customer_contact = self.customer.primarycontact
                self.default_customer_address = self.customer.shifttopartyaddress

            if self.service:
                self.default_gps_location = self.service.gps_location



        super().save(*args, **kwargs)

        # ----------------------------------------
        # DEFAULT TECHNICIANS FROM CRM
        # ----------------------------------------
        if is_new:
            from crmapp.models import WorkAllocation
            techs = set()

            for w in WorkAllocation.objects.filter(service=self.service):
                techs.update(w.technician.all())

            self.technicians.set(techs)

        # ----------------------------------------
        # AUTO SERVICE SCHEDULES + VISITS
        # ----------------------------------------
        if is_new and not self.service_schedules.exists():

            service_dates = []

            if freq.isdigit():
                freq_int = int(freq)
                gap_days = round(365 / freq_int)
                for i in range(freq_int):
                    service_dates.append(
                        self.start_date + relativedelta(days=i * gap_days)
                    )

            elif freq == "weekly":
                for i in range(52):
                    service_dates.append(
                        self.start_date + relativedelta(weeks=i)
                    )

            elif freq == "fortnight":
                for i in range(26):
                    service_dates.append(
                        self.start_date + relativedelta(weeks=2 * i)
                    )

            elif freq == "daily":
                for i in range(365):
                    service_dates.append(
                        self.start_date + relativedelta(days=i)
                    )

            # ----------------------------------------
            # CREATE SCHEDULES + VISITS  ✅ FIX HERE
            # ----------------------------------------
            for date in service_dates:

                schedule = AMCServiceSchedule.objects.create(
                    amc=self,
                    service_date=date
                )

                visit = AMCServiceVisit.objects.create(
                    amc=self,
                    service_date=date,
                    
                )

                visit.technicians.set(self.technicians.all())

            # ----------------------------------------
            # FINAL END DATE + PER VISIT AMOUNT
            # ----------------------------------------
            self.end_date = service_dates[-1]
            self.per_visit_amount = (
                self.total_amount / len(service_dates)
                if service_dates else 0
            )
            self.default_payment_amount = self.per_visit_amount

            super().save(update_fields=["end_date", "per_visit_amount"])

    @property
    def next_service_date(self):
        next_visit = self.visits.filter(
            service_date__gte=timezone.now().date()
        ).order_by("service_date").first()

        return next_visit.service_date if next_visit else None        

    def __str__(self):
        return self.contract_number

# ---------------------------------
# AMC SERVICE SCHEDULE (PLANNED)
# ---------------------------------
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



# ---------------------------------
# SERVICE VISIT MODEL (ACTUAL VISIT)
# ---------------------------------
from crmapp.models import service_management
from crmapp.models import TechWorkList
from dateutil.relativedelta import relativedelta

class AMCServiceVisit(models.Model):
    amc = models.ForeignKey(
        AMCContract,
        on_delete=models.CASCADE,
        related_name="visits"
    )

    # 📅 Actual visit date (editable / reschedulable)
    service_date = models.DateField()

    # 👷 Technicians for THIS visit
    technicians = models.ManyToManyField(
        TechnicianProfile,
        blank=True,
        related_name="amc_visits"
    )

    # 🔗 CRM service created for this visit
    crm_service = models.ForeignKey(
        service_management,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="amc_service_visits"
    )
    crm_service_created_at = models.DateTimeField(null=True, blank=True)

    # 🧠 AUTO ALLOCATION FLAG (ADD THIS 👇)
    auto_allocation_done = models.BooleanField(default=False)

    # -------------------------------
    # ALLOCATION STATE
    # -------------------------------
    allocation_status = models.CharField(
        max_length=20,
        choices=[
            ("PENDING", "Pending"),
            ("ALLOCATED", "Allocated"),
            ("CANCELLED", "Cancelled"),
        ],
        default="PENDING"
    )

    allocation_cancelled_reason = models.TextField(
        blank=True,
        null=True
    )

    remarks = models.TextField(blank=True, null=True)

    # 🔁 Reschedule support
    rescheduled_from = models.DateField(null=True, blank=True)

    next_visit_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)


    def save(self, *args, **kwargs):
        # Safe fallback only
        if not self.next_visit_date and self.amc:
            self.next_visit_date = self.service_date + relativedelta(months=1)
        super().save(*args, **kwargs)

    # -------------------------------------------------
    # ✅ CRM-DRIVEN COMPLETION (READ ONLY)
    # -------------------------------------------------
    @property
    def is_completed(self):
        """
        Visit is completed if ANY CRM work is completed
        """
        if not self.crm_service:
            return False

        return TechWorkList.objects.filter(
            service=self.crm_service,
            status="Completed"
        ).exists()

    @property
    def completed_at(self):
        """
        Completion datetime from CRM
        """
        if not self.crm_service:
            return None

        completed_work = TechWorkList.objects.filter(
            service=self.crm_service,
            status="Completed"
        ).order_by("-completion_datetime").first()

        return completed_work.completion_datetime if completed_work else None

    def __str__(self):
        return f"{self.amc.contract_number} - {self.service_date}"




