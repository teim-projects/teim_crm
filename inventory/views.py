from django.shortcuts import render,redirect
from .models import *
# Create your views here.

def addVendor(request):
  return render(request, 'inventory/add_vendor.html')


def vendorList(request):
  return render(request, 'inventory/vendor_list.html')