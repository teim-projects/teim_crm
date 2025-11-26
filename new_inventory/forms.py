from .models import Vendor, HO, Site, PurchaseOrder, DESTINATION_TYPES, PurchaseOrderItem, GoodsReceiveNote

from .utils import get_destination_queryset,  get_destination_object
from django import forms
from django.forms import inlineformset_factory
from crmapp.models import Branch


# ---------------- VENDOR FORM ----------------

class VendorForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = '__all__'
        label_suffix = ""


# ---------------- HO STAFF FORM ----------------

class HoForm(forms.ModelForm):
    is_manager = forms.BooleanField(
        required=False,
        label="Is Manager?"
    )
    password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        required=True,
        label="Confirm Password"
    )

    class Meta:
        model = HO
        exclude = ("role", "user")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            self.fields["is_manager"].initial = False
        else:
            self.fields["is_manager"].initial = (
                self.instance.role == "HO_manager"
            )
            self.fields["password"].required = False
            self.fields["confirm_password"].required = False

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
        cleaned = super().clean()
        pwd = cleaned.get("password")
        cpwd = cleaned.get("confirm_password")

        if self.instance.pk:
            if pwd or cpwd:
                if not pwd or not cpwd or pwd != cpwd:
                    self.add_error("confirm_password", "Passwords do not match!")
        else:
            if not pwd or not cpwd or pwd != cpwd:
                self.add_error("confirm_password", "Passwords do not match!")

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.role = "HO_manager" if self.cleaned_data.get("is_manager") else "HO_operation"

        if commit:
            instance.save()
        return instance


# ---------------- SITE FORM ----------------

class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = '__all__'
        label_suffix = ""


# ---------------- PURCHASE ORDER FORM ----------------

class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            "vendor",
            "destination_type",
            "destination_id",
            "status",
            "material_supply",
            "freight_charges",           # NEW FIELD
            "quotation_attachment",
        ]
        widgets = {
            "destination_type": forms.Select(attrs={"class": "form-control destination-type"}),
            "destination_id": forms.Select(attrs={"class": "form-control destination-id"}),
            "material_supply": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "quotation_attachment": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-control"}),
            "vendor": forms.Select(attrs={"class": "form-control"}),
            "freight_charges": forms.NumberInput(attrs={"class": "form-control"}),   # NEW
        }

    def __init__(self, *args, **kwargs):
          super().__init__(*args, **kwargs)
    
          # safe default
          self.fields["destination_id"].choices = [("", "---------")]
    
          # determine destination_type (prefers posted data, then initial, then instance)
          dest_type = None
          if self.data.get("destination_type"):
              dest_type = self.data.get("destination_type")
          elif self.initial.get("destination_type"):
              dest_type = self.initial.get("destination_type")
          elif getattr(self, "instance", None) and getattr(self.instance, "destination_type", None):
              dest_type = self.instance.destination_type
    
          if dest_type:
              qs = get_destination_queryset(dest_type)
              self.fields["destination_id"].choices = [("", "---------")] + [
                  (obj.id, str(obj)) for obj in qs
              ]
    
              # set initial to the instance integer id (so the select shows selected option)
              if getattr(self, "instance", None) and getattr(self.instance, "destination_id", None) is not None:
                  self.initial["destination_id"] = self.instance.destination_id
    def clean(self):
        cleaned = super().clean()
        dest_type = cleaned.get("destination_type")

        # Auto-set HO id
        if dest_type == "HO":
            ho = get_destination_queryset("HO").first()
            if ho:
                cleaned["destination_id"] = ho.id

        return cleaned


# ---------------- PURCHASE ORDER ITEM FORM ----------------

class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ["product", "quantity", "rate", "discount", "remarks"]   # NEW FIELDS
        widgets = {
            "product": forms.Select(attrs={"class": "form-control product-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control"}),
            "rate": forms.NumberInput(attrs={"class": "form-control"}),         # NEW
            "discount": forms.NumberInput(attrs={"class": "form-control"}),     # NEW
            "remarks": forms.TextInput(attrs={"class": "form-control"}),
        }


# ---------------- FORMSET FOR ITEMS ----------------

PurchaseOrderItemFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=1,
    can_delete=True
)


# ---------------- GRN FORM ----------------

class GRNForm(forms.ModelForm):
    class Meta:
        model = GoodsReceiveNote
        fields = [
            "received_location_type",
            "received_location_id",
            "received_date",
            "invoice_no",
            "invoice_date",
            "remarks"
        ]
        widgets = {
            "received_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "invoice_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "received_location_type": forms.Select(attrs={"class": "form-control"}),
            "received_location_id": forms.NumberInput(attrs={"class": "form-control"}),
            "invoice_no": forms.TextInput(attrs={"class": "form-control"}),
            "remarks": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }
