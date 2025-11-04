from django.shortcuts import render,redirect
from django.contrib import messages
from .models import *
# Create your views here.



def addVendor(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        mobile_no = request.POST.get('mobile')
        email = request.POST.get('email')
        website = request.POST.get('website')
        company_type = request.POST.get('company_type')
        gst_details = request.POST.get('gst_details')
        office_address = request.POST.get('office_address')
        store_address = request.POST.get('store_address')
        bank_details = request.POST.get('bank_details')
        supplier_category = request.POST.get('supplier_category')

        # ✅ Check duplicate vendor by email or mobile
        if Vendor.objects.filter(mobile=mobile_no).exists():
            messages.error(request, "Vendor with this mobile number already exists.")
            return redirect('add_vendor')

        if Vendor.objects.filter(email=email).exists():
            messages.error(request, "Vendor with this email already exists.")
            return redirect('add_vendor')

        Vendor.objects.create(
            name=name,
            email=email,
            mobile=mobile_no,
            website=website,
            bank_details=bank_details,
            office_address=office_address,
            store_address=store_address,
            company_type=company_type,
            GST_details=gst_details,
            supplier_category=supplier_category
        )

        messages.success(request, "Vendor added successfully!")
        return redirect('vendor_list')  # ✅ Redirect to vendor list after success

    return render(request, 'inventory/add_vendor.html')

def vendorList(request):
  vendor = Vendor.objects.all()
  context = {
    'vendor': vendor
  }
  return render(request, 'inventory/vendor_list.html', context)