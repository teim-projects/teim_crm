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
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
from crmapp.models import (
    service_management,
    Product,
    TechnicianProfile,
    ServiceProductFrequency,
    customer_details,
    Branch,
    WorkAllocation
)
from django.contrib.auth.models import User


# -----------------------------------------
# Helper function for contract number generation
# -----------------------------------------
def generate_contract_number():
    """Generate a unique contract number"""
    import uuid
    return f"AMC-{uuid.uuid4().hex[:8].upper()}"

# -----------------------------------------
# AMC CONTRACT
# -----------------------------------------
class AMCContract(models.Model):
    
    # New fields
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
    
    # Make frequency optional/nullable since we now use product-wise frequencies
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
        """Keep for backward compatibility - returns None if empty"""
        if not self.frequency:
            return None
            
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
    
    def convert_freq_to_days_gap(self, freq_value):
        """Convert frequency string/number to days gap"""
        if freq_value is None:
            return None
            
        freq_str = str(freq_value).lower().strip()
        
        # If it's a number (1-365)
        if freq_str.isdigit():
            freq_int = int(freq_str)
            if freq_int > 0:
                return max(1, round(365 / freq_int))
            return None
            
        # Handle text frequencies
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
        
        # Normalize frequency (for backward compatibility - can be empty now)
        if self.frequency:
            self.frequency = self.clean_frequency()
        else:
            self.frequency = None
        
        # Calculate total amount from service
        if self.service:
            self.total_amount = (
                self.service.total_price_with_gst
                or self.service.total_price
                or self.service.total_charges
                or 0
            )
        
        # Set temporary values for first save
        if is_new:
            self.end_date = self.start_date
            self.per_visit_amount = 0
            
            # Auto-fill default work data from CRM
            if self.customer:
                self.default_customer_contact = self.customer.primarycontact
                self.default_customer_address = self.customer.shifttopartyaddress
            
            if self.service:
                self.default_gps_location = self.service.gps_location
        
        super().save(*args, **kwargs)
        
        # Set default technicians from CRM for new contracts
        if is_new:
            techs = set()
            for w in WorkAllocation.objects.filter(service=self.service):
                techs.update(w.technician.all())
            self.technicians.set(techs)
        
        # Generate schedule for new contracts
        if is_new:
            self.generate_schedule()
    
    # ---------------------------------
    def generate_schedule(self):
        """
        Regenerate all schedules and visits for this AMC contract.
        This will delete existing schedules/visits and create new ones
        based on the current product frequencies.
        """
        from datetime import timedelta
        from crmapp.models import ServiceProductFrequency
        from amc.models import AMCServiceVisit, AMCServiceSchedule
        
        # Delete old schedules and visits
        AMCServiceVisit.objects.filter(amc=self).delete()
        AMCServiceSchedule.objects.filter(amc=self).delete()
        
        product_frequencies = ServiceProductFrequency.objects.filter(
            service=self.service
        )
        
        date_product_pairs = []
        
        for pf in product_frequencies:
            freq_value = pf.frequency
            days_gap = self.convert_freq_to_days_gap(freq_value)
            
            if not days_gap:
                continue
            
            num_visits = max(1, round(365 / days_gap))
            
            for i in range(num_visits):
                visit_date = self.start_date + timedelta(days=i * days_gap)
                date_product_pairs.append({
                    'date': visit_date,
                    'product': pf.product
                })
        
        # If no product frequencies, use fallback logic
        if not date_product_pairs:
            if self.frequency:
                freq = self.frequency
                
                if str(freq).isdigit():
                    freq_int = int(freq)
                    gap_days = round(365 / freq_int)
                    for i in range(freq_int):
                        date_product_pairs.append({
                            'date': self.start_date + timedelta(days=i * gap_days),
                            'product': None
                        })
                elif freq == "weekly":
                    for i in range(52):
                        date_product_pairs.append({
                            'date': self.start_date + timedelta(weeks=i),
                            'product': None
                        })
                elif isinstance(freq, int):

                     total_visits = freq
                    
                     # avoid invalid values
                     if total_visits <= 0:
                         total_visits = 26
                    
                     # calculate gap days
                     gap_days = max(1, round(365 / total_visits))
                    
                     # generate visits
                     for i in range(total_visits):
                        
                         visit_date = self.start_date + timedelta(days=i * gap_days)
                    
                         date_product_pairs.append({
                             'date': visit_date,
                             'product': None
                         })
                elif freq == "daily":
                    for i in range(365):
                        date_product_pairs.append({
                            'date': self.start_date + timedelta(days=i),
                            'product': None
                        })
            else:
                # Default monthly schedule
                for i in range(12):
                    date_product_pairs.append({
                        'date': self.start_date + timedelta(days=30 * i),
                        'product': None
                    })
        
        # Sort by date
        date_product_pairs.sort(key=lambda x: x['date'])
        
        # Create schedules and visits
        for pair in date_product_pairs:
            service_date = pair['date']
            product = pair['product']
            
            # Create schedule (only once per date)
            schedule, created = AMCServiceSchedule.objects.get_or_create(
                amc=self,
                service_date=service_date
            )
            
            # Create visit with product
            visit = AMCServiceVisit.objects.create(
                amc=self,
                service_date=service_date,
                product=product
            )
            
            # Assign technicians
            visit.technicians.set(self.technicians.all())
        
        # Update end date and per visit amount
        if date_product_pairs:
            unique_dates = sorted(set(p['date'] for p in date_product_pairs))
            # FIXED: AMC validity = 1 year from start date
            self.end_date = self.start_date + relativedelta(years=1)
            total_visits = len(date_product_pairs)
            self.per_visit_amount = (
                self.total_amount / total_visits
                if total_visits > 0 else 0
            )
            self.default_payment_amount = self.per_visit_amount
            super().save(update_fields=["end_date", "per_visit_amount", "default_payment_amount"])
    
    # ---------------------------------
    @property
    def next_service_date(self):
        next_visit = self.visits.filter(
            service_date__gte=timezone.now().date()
        ).order_by("service_date").first()
        
        return next_visit.service_date if next_visit else None
    
    # ---------------------------------
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
from django.db import models
from django.utils import timezone
from crmapp.models import (
    service_management,
    Product,
    TechnicianProfile
)


class AMCServiceVisit(models.Model):

    amc = models.ForeignKey(
        'AMCContract',
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
    
    crm_service_created_at = models.DateTimeField(
    null=True,
    blank=True
    
    )

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

    # -------------------------------------------------
    # 🔥 MAIN LOGIC
    # -------------------------------------------------
    def stop_future_visits_for_product(self):

        if not self.product:
            return

        # ❌ STOP SAME PRODUCT FUTURE VISITS
        AMCServiceVisit.objects.filter(
            amc=self.amc,
            product=self.product,
            service_date__gt=self.service_date,
            allocation_status="PENDING"
        ).update(
            allocation_status="CANCELLED",
            allocation_cancelled_reason="Auto stopped after product completion"
        )

        # 🔥 CHECK IF AMC COMPLETE
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