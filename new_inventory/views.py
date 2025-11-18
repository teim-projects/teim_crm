from django.shortcuts import render, HttpResponse
from .models import Vendor
from .forms import VendorForm
from django.shortcuts import render, redirect, get_object_or_404
# Create your views here.

def vendor_add(request):
  if request.method == "POST":
    form = VendorForm(request.POST)
    
    if form.is_valid():
      form.save()
      return HttpResponse("Vendor is added....")
    
  else:
    form = VendorForm()
  return render(request,'inventory/add_vendor.html',{'form':form})

def vendor_list(request):
  vendor = Vendor.objects.all()
  return render(request, 'inventory/vendor_list.html' ,{'vendor':vendor})


def vendor_edit(request, id):
  pass

def vendor_delete(request, id):
  pass
