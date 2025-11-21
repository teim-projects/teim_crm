from .models import Vendor ,HO , Site ,PurchaseOrder,DESTINATION_TYPES, PurchaseOrderItem
from .utils import get_destination_queryset
from crmapp.models import Branch  
from django import forms

class VendorForm(forms.ModelForm):
  class Meta:
    model = Vendor
    fields = '__all__'
    label_suffix = ""

class HoForm(forms.ModelForm):
    is_manager = forms.BooleanField(
        required=False,
        label="Is Manager?"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,   # required on create
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,   # required on create
        label="Confirm Password"
    )

    class Meta:
        model = HO
        exclude = ("role", "user")   # hide role + user fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # --- create vs edit ---
        if not self.instance.pk:
            # CREATE
            self.fields["is_manager"].initial = False
        else:
            # EDIT
            # pre-fill is_manager from instance.role
            self.fields["is_manager"].initial = (
                self.instance.role == "HO_manager"
            )
            # make password optional on edit
            self.fields["password"].required = False
            self.fields["confirm_password"].required = False

    # check contact is exists or not 
    def clean_contact(self):
        contact = self.cleaned_data.get("contact")
        if not contact:
            return contact

        qs = HO.objects.filter(contact=contact)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)

        if qs.exists():
            raise forms.ValidationError("This contact number is already registered.")

        return contact
    
    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("password")
        cpwd = cleaned_data.get("confirm_password")

        # On create → both required and must match
        # On edit → only validate if any password is entered
        if self.instance.pk:
            # EDIT
            if pwd or cpwd:
                if not pwd or not cpwd or pwd != cpwd:
                    self.add_error("confirm_password", "Passwords do not match!")
        else:
            # CREATE
            if not pwd or not cpwd or pwd != cpwd:
                self.add_error("confirm_password", "Passwords do not match!")

        return cleaned_data

    def save(self, commit=True):
        """Only save HO instance + set role. User creation is handled in view."""
        instance = super().save(commit=False)

        instance.role = "HO_manager" if self.cleaned_data.get("is_manager") else "HO_operation"

        if commit:
            instance.save()

        return instance


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = '__all__'
        label_suffix = ""


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "vendor",
            "destination_type",
            "destination_id",
            "status",
            "material_supply",
            "quotation_attachment",
        ]
        widgets = {
            "destination_type": forms.Select(attrs={"class": "form-control destination-type"}),
            "destination_id": forms.Select(attrs={"class": "form-control destination-id"}),
            "material_supply": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "quotation_attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "vendor": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default empty; JS will load options
        self.fields["destination_id"].choices = [("", "---------")]

        if self.instance.pk:  # editing
            qs = get_destination_queryset(self.instance.destination_type)
            self.fields["destination_id"].choices = [("", "---------")] + [
                (obj.id, str(obj)) for obj in qs
            ]
            self.initial["destination_id"] = self.instance.destination_id

    def clean(self):
        cleaned = super().clean()
        dest_type = cleaned.get("destination_type")

        # force HO
        if dest_type == "HO":
            ho = get_destination_queryset("HO").first()
            if ho:
                cleaned["destination_id"] = ho.id
        return cleaned


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["product", "quantity", "remarks"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-control"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "remarks": forms.TextInput(attrs={"class": "form-control"}),
        }

PurchaseOrderItemFormSet = forms.modelformset_factory(
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True
)

