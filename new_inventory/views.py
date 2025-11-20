from django.shortcuts import render, HttpResponse
from .models import Vendor
from crmapp.models import UserProfile
from .forms import *
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
# Create your views here.

# ------------ Vendor Section start here ----------
# Add vendor
def vendor_add(request):
  if request.method == "POST":
    form = VendorForm(request.POST)
    
    if form.is_valid():
      form.save()
      return redirect("vendor_list")
    
  else:
    form = VendorForm()
  return render(request,'inventory/add_vendor.html',{'form':form})

# vendor list
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


# Edit vendor 
def vendor_edit(request, id):
  vendor = get_object_or_404(Vendor, id=id)
  form = VendorForm(request.POST or None, instance=vendor)

  if form.is_valid():
    form.save()
    return redirect("vendor_list")

  return render(request, 'inventory/vendor_edit.html', {'form': form})

# Delete Vendor
def vendor_delete(request, id):
  vendor = get_object_or_404(Vendor, id=id)
  vendor.delete()
  return redirect('vendor_list')

#------------------------ Vendor section end -------------------------------

# ----------------------- Head Office staff section ------------------------
UserModel = get_user_model()
# ------ add ho staff ------
def add_ho_staff(request):
    if request.method == "POST":
        form = HoForm(request.POST)
        if form.is_valid():
            ho = form.save(commit=False)  # role is already set in the form's save()

            # Create a User for this HO
            email = form.cleaned_data.get("email")
            name = form.cleaned_data.get("name")
            contact = form.cleaned_data.get("contact")
            password = form.cleaned_data.get("password")

            # Use contact as username (or fallback to email)
            username = contact or email
            if not username:
                username = (name or "ho_user").replace(" ", "").lower()

            # Ensure username is unique
            base_username = username
            counter = 1
            while UserModel.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = UserModel.objects.create_user(
                username=username,
                email=email,
                first_name=name,
                password=password,
            )

            # ✅ Get or create UserProfile, avoid duplicate user_id
            user_profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": ho.role,
                    "phone": contact,
                },
            )
            if not created:
                user_profile.role = ho.role
                user_profile.phone = contact
                user_profile.save()

            ho.user = user
            ho.save()

            return redirect('ho_list')

    else:
        form = HoForm()

    return render(request, "inventory/add_ho.html", {"form": form})

# ------ ho staff list -------
def ho_list(request):
    search = request.GET.get("search", "")
    role = request.GET.get("role", "")
    

    ho_staff = HO.objects.all()

    # SEARCH
    if search:
        ho_staff = ho_staff.filter(
            Q(name__icontains=search) |
            Q(contact__icontains=search) 
        )

    # FILTERS
    if role:
        ho_staff = ho_staff.filter(role=role)


    # UNIQUE DROPDOWN VALUES
    role = HO.objects.values_list("role", flat=True).distinct()


    # PAGINATION (same as quotation)
    paginator = Paginator(ho_staff, 10)  # 10 vendors per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "ho_staff": page_obj,
        "page_obj": page_obj,
        "role": role,
        "querystring": request.GET.urlencode(),
    }

    return render(request, "inventory/list_ho.html", context)

#  ------- edit staff list -----
def ho_edit(request, pk):
    ho = get_object_or_404(HO, id=pk)

    if request.method == "POST":
        form = HoForm(request.POST, instance=ho)
        if form.is_valid():
            ho_obj = form.save(commit=False)

            # update linked user if exists
            user = ho_obj.user
            password = form.cleaned_data.get("password")

            if user:
                user.first_name = ho_obj.name
                user.email = ho_obj.email
                if password:  # only if user entered new password
                    user.set_password(password)
                user.save()

            ho_obj.save()
            return redirect("ho_list")
    else:
        form = HoForm(instance=ho)

    return render(request, "inventory/add_ho.html", {"form": form, "ho": ho})

# ------ delete staff ------
def ho_delete(request, pk):
  ho = get_object_or_404(HO, id=pk)
  ho.delete()
  return redirect('ho_list')

# ----------------- Vendor section end ---------------
# ----------------- Site section start ---------------
# ---- add site -----
def add_site(request):
  if request.method == "POST":
    form = SiteForm(request.POST)
    
    if form.is_valid():
      form.save()
      return redirect("site_list")
    
  else:
    form = SiteForm()
  return render(request,'inventory/add_site.html',{'form':form})
