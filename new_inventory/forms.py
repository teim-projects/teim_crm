from .models import Vendor
from django import forms

class VendorForm(forms.ModelForm):
  class Meta:
    model = Vendor
    fields = '__all__'
    label_suffix = ""
  
