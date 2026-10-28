from django import forms
from .models import AMCContract, AMCServiceVisit, AMCServiceSchedule
from crmapp.models import (
    customer_details,
    service_management,
    TechnicianProfile,
    Branch
)


# -------------------------------------------------------
# AMC CONTRACT FORM
# -------------------------------------------------------
class AMCContractForm(forms.ModelForm):

    customer = forms.ModelChoiceField(
        queryset=customer_details.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Customer"
    )

    service = forms.ModelChoiceField(
        queryset=service_management.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
        required=True,
        label="Service"
    )

    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        widget=forms.Select(attrs={"class": "form-control"}),
        required=False,
        label="Branch"
    )

    technicians = forms.ModelMultipleChoiceField(
        queryset=TechnicianProfile.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control",
                "id": "technicians-dropdown"
            }
        ),
        required=False
    )


    
    FREQUENCY_CHOICES = [
        ("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"),
        ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8"),
        ("9", "9"), ("10", "10"), ("11", "11"), ("12", "12"),
        ("Weekly", "Weekly"),
        ("Fortnight", "Fortnight"),
        ("Daily", "Daily"),
    ]

    frequency = forms.ChoiceField(
        choices=FREQUENCY_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Frequency (Services / Year)"
    )

    class Meta:
        model = AMCContract
        fields = [
            "customer",
            "service",
            "branch",
            "amc_type",
            "start_date",
            "frequency",
            "technicians",
            "service_description",
            "notes",
        ]

        widgets = {
            "amc_type": forms.Select(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            
            "service_description": forms.Textarea(
                attrs={"rows": 3, "class": "form-control"}
            ),
            "notes": forms.Textarea(
                attrs={"rows": 3, "class": "form-control"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If editing an existing AMC
        if self.instance and self.instance.pk:
            # Lock start date on edit
            self.fields["start_date"].widget.attrs["readonly"] = True

            # Load services of that customer
            self.fields["service"].queryset = service_management.objects.filter(
                customer=self.instance.customer
            )

            # Pre-fill technicians
            self.fields["technicians"].initial = self.instance.technicians.all()



from django import forms
from .models import AMCServiceVisit, AMCServiceSchedule
from crmapp.models import TechnicianProfile


class AMCServiceVisitForm(forms.ModelForm):

    service_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control"
            }
        ),
        label="Visit Date"
    )

    technicians = forms.ModelMultipleChoiceField(
        queryset=TechnicianProfile.objects.all(),
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control",
                "size": "5"
            }
        ),
        required=False,
        label="Technicians"
    )

    class Meta:
        model = AMCServiceVisit
        fields = [
            "service_date",
            "technicians",
            "remarks",
        ]

        widgets = {
            "remarks": forms.Textarea(
                attrs={
                    "rows": 3,
                    "class": "form-control",
                    "placeholder": "Optional remarks"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 🚫 Lock editing if visit already completed
        if self.instance and self.instance.pk:
            
            schedule = AMCServiceSchedule.objects.filter(
                amc=self.instance.amc,
                service_date=self.instance.service_date
            ).first()
            
            if schedule and schedule.is_completed:
                for field in self.fields.values():
                    field.disabled = True

    def save(self, commit=True):
        visit = super().save(commit=False)

        # 🔁 Track reschedule
        if self.instance.pk:
            old_date = AMCServiceVisit.objects.get(pk=self.instance.pk).service_date
            if old_date != visit.service_date:
                visit.rescheduled_from = old_date

        if commit:
            visit.save()
            self.save_m2m()

        return visit


from django import forms
from .models import AMCContract
from crmapp.models import TechnicianProfile


class AMCDefaultAssignmentForm(forms.ModelForm):

    technicians = forms.ModelMultipleChoiceField(
        queryset=TechnicianProfile.objects.all(),
        required=False,
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-control technician-select"
            }
        )
    )

    class Meta:
        model = AMCContract
        fields = [
            "technicians",
            "default_customer_contact",
            "default_customer_address",
            "default_gps_location",
            "default_payment_amount",
            "default_payment_status",
            "default_work_description",
        ]


        widgets = {
            "default_customer_contact": forms.TextInput(attrs={"class": "form-control"}),
            "default_customer_address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "default_gps_location": forms.URLInput(attrs={"class": "form-control"}),
            "default_payment_amount": forms.NumberInput(attrs={"class": "form-control"}),
            "default_payment_status": forms.Select(attrs={"class": "form-select"}),
            "default_work_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }




from django import forms
from crmapp.models import WorkAllocation

class AMCWorkAllocationForm(forms.ModelForm):
    class Meta:
        model = WorkAllocation
        fields = [
            "fullname",
            "customer_contact",
            "customer_address",
            "gps_location",
            "work_description",
            "customer_payment_status",
            "payment_amount",
        ]

        widgets = {
            "fullname": forms.TextInput(attrs={"class": "form-control"}),
            "customer_contact": forms.TextInput(attrs={"class": "form-control"}),
            "customer_address": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "gps_location": forms.URLInput(attrs={"class": "form-control"}),
            "work_description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "customer_payment_status": forms.Select(
                attrs={"class": "form-select"}
            ),
            "payment_amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01"}
            ),
        }