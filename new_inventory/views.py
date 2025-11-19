from django.shortcuts import render, HttpResponse
from .models import Vendor
from .forms import VendorForm
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
# Create your views here.

def vendor_add(request):
  if request.method == "POST":
    form = VendorForm(request.POST)
    
    if form.is_valid():
      form.save()
      return redirect("vendor_list")
    
  else:
    form = VendorForm()
  return render(request,'inventory/add_vendor.html',{'form':form})


def vendor_list(request):

    search = request.GET.get("search", "")
    company_type = request.GET.get("company_type", "")
    supplier_category = request.GET.get("supplier_category", "")

    vendors = Vendor.objects.all()

    # SEARCH
    if search:
        vendors = vendors.filter(
            Q(name__icontains=search) |
            Q(mobile__icontains=search) |
            Q(office_poc_name__icontains=search) |
            Q(office_poc_phone__icontains=search) |
            Q(store_poc_name__icontains=search) |
            Q(store_poc_phone__icontains=search)
        )

    # FILTERS
    if company_type:
        vendors = vendors.filter(compony_type=company_type)

    if supplier_category:
        vendors = vendors.filter(supplier_category=supplier_category)

    # UNIQUE DROPDOWN VALUES
    company_types = Vendor.objects.values_list("compony_type", flat=True).distinct()
    supplier_categories = Vendor.objects.values_list("supplier_category", flat=True).distinct()

    # PAGINATION (same as quotation)
    paginator = Paginator(vendors, 10)  # 10 vendors per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "vendor": page_obj,
        "page_obj": page_obj,
        "company_types": company_types,
        "supplier_categories": supplier_categories,
        "querystring": request.GET.urlencode(),
    }

    return render(request, "inventory/vendor_list.html", context)



def vendor_edit(request, id):
  vendor = get_object_or_404(Vendor, id=id)
  form = VendorForm(request.POST or None, instance=vendor)

  if form.is_valid():
    form.save()
    return redirect("vendor_list")

  return render(request, 'inventory/vendor_edit.html', {'form': form})

def vendor_delete(request, id):
  vendor = get_object_or_404(Vendor, id=id)
  vendor.delete()
  return redirect('vendor_list')
