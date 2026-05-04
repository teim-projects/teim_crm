from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from crmapp.models import UserProfile, Product,ProductRequiredItem
from crmapp.models import UserProfile
from .utils import get_destination_object

from .models import *
from .forms import *
from .utils import *
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils.http import urlencode
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse
from decimal import Decimal
from django.db.models import Sum

from django.db import transaction
from django.contrib import messages
import datetime  
from num2words import num2words
import re
from crmapp.custom_filters import price_in_words
from django.utils.dateparse import parse_date
from crmapp.decorators import role_required

state_map = {
        'Andaman and Nicobar Islands': {'code': 35, 'shortcut': 'AN'},
        'Andhra Pradesh': {'code': 37, 'shortcut': 'AP'},
        'Arunachal Pradesh': {'code': 12, 'shortcut': 'AR'},
        'Assam': {'code': 18, 'shortcut': 'AS'},
        'Bihar': {'code': 10, 'shortcut': 'BR'},
        'Chandigarh': {'code': 4, 'shortcut': 'CH'},
        'Chhattisgarh': {'code': 22, 'shortcut': 'CG'},
        'Dadra and Nagar Haveli and Daman and Diu': {'code': 26, 'shortcut': 'DNHDD'},
        'Delhi': {'code': 7, 'shortcut': 'DL'},
        'Goa': {'code': 30, 'shortcut': 'GA'},
        'Gujarat': {'code': 24, 'shortcut': 'GJ'},
        'Haryana': {'code': 6, 'shortcut': 'HR'},
        'Himachal Pradesh': {'code': 2, 'shortcut': 'HP'},
        'Jammu and Kashmir': {'code': 1, 'shortcut': 'JK'},
        'Jharkhand': {'code': 20, 'shortcut': 'JH'},
        'Karnataka': {'code': 29, 'shortcut': 'KA'},
        'Kerala': {'code': 32, 'shortcut': 'KL'},
        'Ladakh': {'code': 38, 'shortcut': 'LA'},
        'Lakshadweep': {'code': 31, 'shortcut': 'LD'},
        'Madhya Pradesh': {'code': 23, 'shortcut': 'MP'},
        'Maharashtra': {'code': 27, 'shortcut': 'MH'},
        'Manipur': {'code': 14, 'shortcut': 'MN'},
        'Meghalaya': {'code': 17, 'shortcut': 'ML'},
        'Mizoram': {'code': 15, 'shortcut': 'MZ'},
        'Nagaland': {'code': 13, 'shortcut': 'NL'},
        'Odisha': {'code': 21, 'shortcut': 'OD'},
        'Other Country': {'code': 99, 'shortcut': 'OC'},
        'Other Territory': {'code': 97, 'shortcut': 'OT'},
        'Puducherry': {'code': 34, 'shortcut': 'PY'},
        'Punjab': {'code': 3, 'shortcut': 'PB'},
        'Rajasthan': {'code': 8, 'shortcut': 'RJ'},
        'Sikkim': {'code': 11, 'shortcut': 'SK'},
        'Tamil Nadu': {'code': 33, 'shortcut': 'TN'},
        'Telangana': {'code': 36, 'shortcut': 'TS'},
        'Tripura': {'code': 16, 'shortcut': 'TR'},
        'Uttar Pradesh': {'code': 9, 'shortcut': 'UP'},
        'Uttarakhand': {'code': 5, 'shortcut': 'UK'},
        'West Bengal': {'code': 19, 'shortcut': 'WB'}
        } 



# ------- load destination --------
def load_destinations(request):
    dest_type = request.GET.get("destination_type")
    qs = get_destination_queryset(dest_type)

    data = [{"id": obj.id, "name": str(obj)} for obj in qs]
    return JsonResponse({"results": data})



# ---------------- Product details API (FOR PO AUTO-FILL) ----------------
@login_required
def get_product_details(request, product_id):
    try:
        # ✅ FIX: use primary key (id), not product_id
        product = Product.objects.get(pk=product_id)

        return JsonResponse({
            "description": product.description or "",
            "unit": product.standard_unit or ""
        })

    except Product.DoesNotExist:
        return JsonResponse({
            "description": "",
            "unit": ""
        })





# ------------ Vendor Section start here ----------
@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def vendor_add(request):
    
    if request.method == "POST":
        form = VendorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("vendor_list")
    else:
        form = VendorForm()
    return render(request, 'inventory/add_vendor.html', {'form': form , "state_map":state_map})

@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def vendor_list(request):
    search = request.GET.get("search", "")
    company_type = request.GET.get("company_type", "")
    supplier_category = request.GET.get("supplier_category", "")

    vendors = Vendor.objects.all()

    if search:
        vendors = vendors.filter(
            Q(name__icontains=search) |
            Q(mobile__icontains=search) |
            Q(office_poc_name__icontains=search) |
            Q(office_poc_phone__icontains=search) |
            Q(store_poc_name__icontains=search) |
            Q(store_poc_phone__icontains=search)
        )

    if company_type:
        vendors = vendors.filter(company_type=company_type)

    if supplier_category:
        vendors = vendors.filter(supplier_category=supplier_category)

    company_types = Vendor.objects.values_list("company_type", flat=True).distinct()
    supplier_categories = Vendor.objects.values_list("supplier_category", flat=True).distinct()

    paginator = Paginator(vendors, 10)
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

@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def vendor_edit(request, id):
    vendor = get_object_or_404(Vendor, id=id)
    form = VendorForm(request.POST or None, instance=vendor)

    if form.is_valid():
        form.save()
        return redirect("vendor_list")

    return render(request, 'inventory/vendor_edit.html', {'form': form,   "vendor": vendor, "state_map":state_map})

@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def vendor_delete(request, id):
    vendor = get_object_or_404(Vendor, id=id)
    vendor.delete()
    return redirect('vendor_list')


# ----------------------- Head Office staff section ------------------------
UserModel = get_user_model()
@login_required
@role_required(['admin',"HO_manager"])
def add_ho_staff(request):
    role = request.user.userprofile.role 
    if request.method == "POST":
        form = HoForm(request.POST)
        if form.is_valid():
            ho = form.save(commit=False)

            email = form.cleaned_data.get("email")
            name = form.cleaned_data.get("name")
            contact = form.cleaned_data.get("contact")
            password = form.cleaned_data.get("password")

            username = contact or email or (name.replace(" ", "").lower())

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
        print("role",role)
    return render(request, "inventory/add_ho.html", {"form": form, "role":role})

@login_required
@role_required(['admin',"HO_manager"])
def ho_list(request):
    search = request.GET.get("search", "")
    role = request.GET.get("role", "")

    ho_staff = HO.objects.all()

    if search:
        ho_staff = ho_staff.filter(
            Q(name__icontains=search) |
            Q(contact__icontains=search)
        )

    if role:
        ho_staff = ho_staff.filter(role=role)

    role = HO.objects.values_list("role", flat=True).distinct()

    paginator = Paginator(ho_staff, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "ho_staff": page_obj,
        "page_obj": page_obj,
        "role": role,
        "querystring": request.GET.urlencode(),
    }

    return render(request, "inventory/list_ho.html", context)


@login_required
@role_required(['admin',"HO_manager"])
def ho_edit(request, pk):
    ho = get_object_or_404(HO, id=pk)

    if request.method == "POST":
        form = HoForm(request.POST, instance=ho)
        if form.is_valid():
            ho_obj = form.save(commit=False)

            user = ho_obj.user
            password = form.cleaned_data.get("password")

            if user:
                user.first_name = ho_obj.name
                user.email = ho_obj.email
                if password:
                    user.set_password(password)
                user.save()

            ho_obj.save()
            return redirect("ho_list")
    else:
        form = HoForm(instance=ho)

    return render(request, "inventory/add_ho.html", {"form": form, "ho": ho})

@login_required
@role_required(['admin',"HO_manager"])
def ho_delete(request, pk):
    ho = get_object_or_404(HO, id=pk)
    ho.delete()
    return redirect('ho_list')


# ----------------- Site section -----------------------

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def add_site(request):
    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            site = form.save()                              # ← added: store the saved object
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'site': {
                        'id': site.id,
                        'name': site.name,
                    }
                })
            return redirect("site_list")
        else:
            # Optional: handle AJAX form errors (you can keep or remove this block later)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors.as_json()
                }, status=400)
    else:
        form = SiteForm()

    return render(request, "inventory/add_site.html", {"form": form})

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def site_list(request):
    search = request.GET.get("search", "")
    sites = Site.objects.all()

    if search:
        sites = sites.filter(
            Q(name__icontains=search) |
            Q(phone__icontains=search) |
            Q(contact_person__icontains=search)
        )

    paginator = Paginator(sites, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "site": page_obj,
        "page_obj": page_obj,
        "querystring": request.GET.urlencode(),
    }

    return render(request, "inventory/site_list.html", context)

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def site_edit(request, id):
    site = get_object_or_404(Site, id=id)
    form = SiteForm(request.POST or None, instance=site)

    if form.is_valid():
        form.save()
        return redirect("site_list")

    return render(request, "inventory/add_site.html", {"form": form, "site": site})

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def site_delete(request, id):
    site = get_object_or_404(Site, id=id)
    site.delete()
    return redirect("site_list")



from django.http import JsonResponse
from crmapp.models import ProductRequiredItem

def get_required_items(request, product_id):
    items = ProductRequiredItem.objects.filter(product_id=product_id)

    data = [
        {"id": i.id, "name": i.item_name}
        for i in items
    ]

    return JsonResponse({"items": data})
# ------------------ Purchase order section --------------- 
@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def purchase_order_create(request):
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, request.FILES)
        formset = PurchaseOrderItemFormSet(
            request.POST,
            queryset=PurchaseOrderItem.objects.none(),
            prefix="items"
        )

        if form.is_valid() and formset.is_valid():
            po = form.save(commit=False)
            po.created_by_user = request.user
            po.save()

            items = formset.save(commit=False)
            for item in items:
                item.purchase_order = po
                item.save()

            sub_products = request.POST.getlist("sub_product")
            sub_item_ids = request.POST.getlist("sub_item_id")
            sub_qtys = request.POST.getlist("sub_qty")
            sub_rates = request.POST.getlist("sub_rate")
            sub_units = request.POST.getlist("sub_unit")
            sub_gsts = request.POST.getlist("sub_gst")
            
            for i in range(len(sub_item_ids)):
                if sub_item_ids[i]:
                    PurchaseOrderSubItem.objects.create(
                        purchase_order=po,
                        product_id=sub_products[i] or None,
                        sub_item_id=sub_item_ids[i],
                        quantity=sub_qtys[i] or 0,
                        rate=sub_rates[i] or 0,
                        unit=sub_units[i],
                        gst_rate=sub_gsts[i] or 0,
                    )              

            return redirect("purchase_order_list")

    else:
        form = PurchaseOrderForm()
        formset = PurchaseOrderItemFormSet(
            queryset=PurchaseOrderItem.objects.none(),
            prefix="items"
        )

    return render(request, "inventory/purchase_order_form.html", {
        "form": form,
        "formset": formset,
        "products": Product.objects.all(),
    })


# ------------------ Purchase order list ---------------------

@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def purchase_order_list(request):
    search = request.GET.get("search", "")
    destination_type = request.GET.get("destination_type", "")
    status = request.GET.get("status", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")

    po_list = PurchaseOrder.objects.all().order_by("-created_at")

    user = request.user.username

    # 🔐 ROLE BASED FILTER
    if request.user.userprofile.role == "branch_manager":
        branch_id = BranchManager.objects.get(mobile_no = user).branch.id
        po_list = po_list.filter(
            destination_type ="BRANCH",
            destination_id = branch_id
        )
    
    elif request.user.userprofile.role == "admin":
        po_list = PurchaseOrder.objects.all().order_by("-created_at")
    if search:
        po_list = po_list.filter(
            Q(po_no__icontains=search) |
            Q(vendor__name__icontains=search) |
            Q(vendor__mobile__icontains=search)
        )

    if destination_type:
        po_list = po_list.filter(destination_type=destination_type)

    if status:
        po_list = po_list.filter(status=status)

    if from_date and to_date:
        po_list = po_list.filter(
            created_at__date__gte=from_date,
            created_at__date__lte=to_date
        )

    filter_count = po_list.count()

    paginator = Paginator(po_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    start_index = page_obj.start_index() - 1

    context = {
        "page_obj": page_obj,
        "querystring": request.GET.urlencode(),
        "filter_count": filter_count,
        "start_index": start_index,
    }

    return render(request, "inventory/purchase_order_list.html", context)


# ------------------ Purchase Order Edit ---------------------

@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def purchase_order_edit(request, id):
    po = get_object_or_404(PurchaseOrder, id=id)
    dest_obj = get_destination_object(po.destination_type, po.destination_id)
    dest_label = str(dest_obj) if dest_obj else ""
# GET existing sub items
    sub_items = po.sub_items.all()
    
    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, request.FILES, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po, prefix="items")
    
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
    
            # 🔥 DELETE OLD SUB ITEMS
            po.sub_items.all().delete()
    
            # 🔥 SAVE NEW SUB ITEMS (same as create)
            sub_products = request.POST.getlist("sub_product")
            sub_item_ids = request.POST.getlist("sub_item_id")
            sub_qtys = request.POST.getlist("sub_qty")
            sub_rates = request.POST.getlist("sub_rate")
            sub_units = request.POST.getlist("sub_unit")
            sub_gsts = request.POST.getlist("sub_gst")
    
            for i in range(len(sub_item_ids)):
                if sub_item_ids[i]:
                    PurchaseOrderSubItem.objects.create(
                        purchase_order=po,
                        product_id=sub_products[i] or None,
                        sub_item_id=sub_item_ids[i],
                        quantity=sub_qtys[i] or 0,
                        rate=sub_rates[i] or 0,
                        unit=sub_units[i],
                        gst_rate=sub_gsts[i] or 0,
                    )
    
            return redirect("purchase_order_list")
        
        else:
            # TEMP: surface errors to console/log so you can see what's wrong
            import logging
            logger = logging.getLogger(__name__)
            logger.error("PO form errors: %s", form.errors.as_json())
            for i, f in enumerate(formset.forms):
                logger.error("Formset form %d errors: %s", i, f.errors.as_json())
            logger.error("Formset non_form_errors: %s", formset.non_form_errors())

    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po, prefix="items")

    return render(request, "inventory/purchase_order_edit.html", {
        "form": form,
        "formset": formset,
        "po": po,
        "sub_items": sub_items,
        "products": Product.objects.all(),
        "destination_initial": {"id": po.destination_id, "label": dest_label}
    })


# ------------------ Purchase Order Delete ---------------------

@login_required
@role_required(['admin',"HO_operation","HO_manager"])
def purchase_order_delete(request, id):
    po = get_object_or_404(PurchaseOrder, id=id)
    po.delete()
    return redirect("purchase_order_list")



#---------------------PDF------------------------

@login_required

def purchase_order_pdf(request, id):
    """
    Render PO PDF. Use ?download=1 to force download (attachment).
    Without ?download=1 the PDF will be served inline so the browser can open it.
    """
    po = get_object_or_404(PurchaseOrder, id=id)
    total_amount_in_words = price_in_words(po.grand_total)

    details = get_destination_details(po.destination_type, po.destination_id)
    destination_display = format_destination_display(details) if details else "Not specified"
  
    context = {
        "po": po,
        "total_amount_in_words": total_amount_in_words,
        "destination_details": details,
        "destination_display": destination_display
    }

    # -------------------------
    # RENDER PDF
    # -------------------------
    template = get_template('inventory/purchase_order_pdf.html')
    html = template.render(context)

    # Decide disposition: inline (view) or attachment (download)
    download_flag = request.GET.get("download", "") in ("1", "true", "yes")
    disposition_type = "attachment" if download_flag else "inline"

    # sanitize filename (remove unsafe chars)
    safe_po_no = re.sub(r"[^\w\-_\. ]", "_", str(po.po_no))
    filename = f"PO_{safe_po_no}.pdf"

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'{disposition_type}; filename="{filename}"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        # you can log pisa_status for details
        return HttpResponse("Error generating PDF", status=500)

    return response

#----------------------------------GRN------------------------------------
@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def grn_create(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    po_items = po.items.all()
    
    # 🔥 ADD THIS
    po_sub_items = po.sub_items.all()

    # compute remaining for each PO item (already-received across previous GRNs)
    remaining_by_item = {}
    for pi in po_items:
        s = GoodsReceiveNoteItem.objects.filter(po_item=pi).aggregate(total=Sum("received_qty"))["total"]
        already = Decimal(s or 0)
        remaining = Decimal(pi.quantity or 0) - already
        if remaining < 0:
            remaining = Decimal("0.00")
        remaining_by_item[pi.id] = remaining

    for pi in po_items:
        pi.remaining = remaining_by_item.get(pi.id, Decimal("0.00"))

    # 🔥 SUB ITEMS REMAINING
    for si in po_sub_items:
        s = GoodsReceiveNoteSubItem.objects.filter(po_sub_item=si).aggregate(total=Sum("received_qty"))["total"]
        already = Decimal(s or 0)
        remaining = Decimal(si.quantity or 0) - already
    
        if remaining < 0:
            remaining = Decimal("0.00")
    
        si.remaining = remaining        

    # destination display values
    po_dest_type = getattr(po, "destination_type", None)
    po_dest_id = getattr(po, "destination_id", None)
    dest_obj = get_destination_object(po_dest_type, po_dest_id)
    dest_label = str(dest_obj) if dest_obj else ""

    if request.method == "POST":
        form = GRNForm(request.POST, request.FILES)
        if form.is_valid():
            errors = []
            item_inputs = []
            sub_inputs = []

            for si in po_sub_items:
                raw = request.POST.get(f"sub_received_qty_{si.id}", "").strip()
            
                if raw in ("", None):
                    continue
            
                try:
                    received_qty = Decimal(raw)
                except Exception:
                    errors.append(f"Invalid quantity for {si.sub_item.item_name}")
                    continue
            
                if received_qty <= 0:
                    continue
            
                if received_qty > si.remaining:
                    errors.append(f"{si.sub_item.item_name} exceeds remaining ({si.remaining})")
                    continue
            
                sub_inputs.append({
                    "si": si,
                    "qty": received_qty,
                    "batch": request.POST.get(f"sub_batch_{si.id}"),
                    "mfg": request.POST.get(f"sub_mfg_{si.id}"),
                    "exp": request.POST.get(f"sub_exp_{si.id}"),
                    "remarks": request.POST.get(f"sub_remarks_{si.id}")
                })            
            
            # gather per-item inputs first for validations
            for pi in po_items:
                raw = request.POST.get(f"received_qty_{pi.id}", "").strip()
                if raw in ("", None):
                    continue
                try:
                    received_qty = Decimal(raw)
                except Exception:
                    errors.append(f"Invalid quantity for {pi.product.product_name}.")
                    continue

                if received_qty <= 0:
                    continue

                # re-check remaining from DB
                s = GoodsReceiveNoteItem.objects.filter(po_item=pi).aggregate(total=Sum("received_qty"))["total"]
                already_db = Decimal(s or 0)
                remaining_db = Decimal(pi.quantity or 0) - already_db
                if remaining_db <= 0:
                    errors.append(f"{pi.product.product_name} is already fully received.")
                    continue
                if received_qty > remaining_db:
                    errors.append(f"Received qty for {pi.product.product_name} exceeds remaining ({remaining_db}).")
                    continue

                # collect optional fields
                batch_no = request.POST.get(f"batch_no_{pi.id}", "").strip() or None
                mfg_str = request.POST.get(f"mfg_{pi.id}", "").strip() or None
                exp_str = request.POST.get(f"exp_{pi.id}", "").strip() or None
                remarks = request.POST.get(f"remarks_{pi.id}", "").strip() or None

                item_inputs.append({
                    "pi": pi,
                    "received_qty": received_qty,
                    "batch_no": batch_no,
                    "mfg_str": mfg_str,
                    "exp_str": exp_str,
                    "remarks": remarks,
                })

            if errors:
                for e in errors:
                    messages.error(request, e)
            else:
                try:
                    with transaction.atomic():
                        # create and save GRN (don't commit yet)
                        grn = form.save(commit=False)
                        grn.purchase_order = po
                        grn.created_by = request.user
                        grn.destination_type = form.cleaned_data["destination_type"]
                        grn.destination_id = form.cleaned_data["destination_id"]

                        # GRN-level batch: if user provided batch_no in form, use/get the Batch,
                        # otherwise create a new Batch for this GRN
                        grn_batch_no = form.cleaned_data.get("batch_no") or None
                        if grn_batch_no:
                            grn_batch, _ = Batch.objects.get_or_create(batch_no=grn_batch_no)
                        else:
                            grn_batch = Batch.objects.create()

                        grn.batch = grn_batch
                        grn.save()

                        items_created = 0
                        for it in item_inputs:
                            pi = it["pi"]
                            gri = GoodsReceiveNoteItem(
                                grn=grn,
                                po_item=pi,
                                product=pi.product,
                                ordered_qty=pi.quantity,
                                received_qty=it["received_qty"],
                                remarks=(it["remarks"][:255] if it["remarks"] else None),
                            )

                            # per-item override: if the item specified its own batch_no, pass it
                            if it["batch_no"]:
                                gri._batch_no_str = it["batch_no"]

                            # parse dates (expecting YYYY-MM-DD). If invalid, ignore.
                            if it["mfg_str"]:
                                try:
                                    gri._manufacturing_date = datetime.date.fromisoformat(it["mfg_str"])
                                except Exception:
                                    pass
                            if it["exp_str"]:
                                try:
                                    gri._expiry_date = datetime.date.fromisoformat(it["exp_str"])
                                except Exception:
                                    pass

                            gri.save()
                            items_created += 1
                        # 🔥 SAVE SUB ITEMS
                        for sub in sub_inputs:
                            si = sub["si"]
                        
                            GoodsReceiveNoteSubItem.objects.create(
                                grn=grn,
                                po_sub_item=si,
                                sub_item=si.sub_item,
                                ordered_qty=si.quantity,
                                received_qty=sub["qty"],
                                batch_no=sub["batch"],
                                mfg_date=sub["mfg"] or None,
                                exp_date=sub["exp"] or None,
                                remarks=sub["remarks"]
                            )
                        if items_created == 0 and len(sub_inputs) == 0:
                            raise ValueError("No GRN items or sub-items were created.")

                        # Recompute PO item remaining from DB to decide PO status
                        all_done = True
                        for pi in po_items:
                            s2 = GoodsReceiveNoteItem.objects.filter(po_item=pi).aggregate(total=Sum("received_qty"))["total"]
                            already2 = Decimal(s2 or 0)
                            remaining2 = Decimal(pi.quantity or 0) - already2
                            if remaining2 > 0:
                                all_done = False
                                break

                        # 🔥 PROCESS SUB ITEMS
                        


                        po.status = "CLOSED" if all_done else "PARTIALLY_RECEIVED"
                        po.save()

                        messages.success(request, f"GRN {grn.grn_no or ''} created successfully.")
                        return redirect("grn_list")

                except Exception as e:
                    messages.error(request, f"Error creating GRN: {e}")
        else:
            messages.error(request, "Please fix the errors in the form.")

    else:
        # GET request — prefill form with destination values
        form = GRNForm(initial={"destination_type": po_dest_type, "destination_id": po_dest_id})

    return render(request, "inventory/grn_create.html", {
        "form": form,
        "po": po,
        "po_items": po_items,
        "po_sub_items": po_sub_items,
        "destination_initial": {"id": po_dest_id, "label": dest_label},
        "remaining_by_item": remaining_by_item,
    })

@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def grn_list(request):
    qs = GoodsReceiveNote.objects.select_related("purchase_order", "purchase_order__vendor").all().order_by("-created_at")

    user = request.user.username

    # 🔐 ROLE BASED FILTER
    if request.user.userprofile.role == "branch_manager":
        branch_id = BranchManager.objects.get(mobile_no = user).branch.id
        qs = qs.filter(
            destination_type ="BRANCH",
            destination_id = branch_id
        )
    
    elif request.user.userprofile.role == "admin":
        qs = GoodsReceiveNote.objects.select_related("purchase_order", "purchase_order__vendor").all().order_by("-created_at")

    # --- Search ---
    search = (request.GET.get("search") or "").strip()
    if search:
        # if the user typed a number, we'll try matching PO id or PO no as well
        q = Q(purchase_order__vendor__name__icontains=search) | Q(purchase_order__vendor__mobile__icontains=search)
        # match PO number partially
        q |= Q(purchase_order__po_no__icontains=search)
        # if numeric, try matching purchase_order id
        if search.isdigit():
            q |= Q(purchase_order__id=int(search))
        qs = qs.filter(q)

    # --- Date filter (inclusive) ---
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    if from_date:
        qs = qs.filter(received_date__gte=from_date)
    if to_date:
        qs = qs.filter(received_date__lte=to_date)

    # --- Pagination ---
    page = request.GET.get("page", 1)
    per_page = 10  # change page size if desired
    paginator = Paginator(qs, per_page)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # template expects `grns` to be the list used in the table loop, and page_obj for paging controls
    grns = page_obj.object_list

    # build querystring without the `page` param so pagination links can append page=...
    params = request.GET.copy()
    if "page" in params:
        params.pop("page")
    querystring = params.urlencode()

    return render(request, "inventory/grn_list.html", {
        "grns": grns,
        "page_obj": page_obj,
        "querystring": querystring,
    })
    
@login_required
@role_required(["admin", "HO_operation", "HO_manager"])
def grn_edit(request, pk):
    grn = get_object_or_404(GoodsReceiveNote, pk=pk)

    items = grn.items.select_related("batch", "product")
    sub_items = grn.sub_items.select_related("sub_item")   # 🔥 ADD THIS

    if request.method == "POST":
        try:
            with transaction.atomic():

                # ✅ UPDATE MAIN ITEMS
                for item in items:
                    if not item.batch:
                        continue

                    mfg_str = request.POST.get(f"mfg_{item.id}")
                    exp_str = request.POST.get(f"exp_{item.id}")

                    batch = item.batch

                    if mfg_str:
                        batch.manufacturing_date = datetime.date.fromisoformat(mfg_str)

                    if exp_str:
                        batch.expiry_date = datetime.date.fromisoformat(exp_str)

                    batch.save(update_fields=["manufacturing_date", "expiry_date"])


                # 🔥 UPDATE SUB ITEMS
                for sub in sub_items:
                    mfg_str = request.POST.get(f"sub_mfg_{sub.id}")
                    exp_str = request.POST.get(f"sub_exp_{sub.id}")

                    if mfg_str:
                        sub.mfg_date = datetime.date.fromisoformat(mfg_str)

                    if exp_str:
                        sub.exp_date = datetime.date.fromisoformat(exp_str)

                    sub.save(update_fields=["mfg_date", "exp_date"])


                messages.success(request, "GRN updated successfully.")
                return redirect("grn_list")

        except Exception as e:
            messages.error(request, f"Update failed: {e}")

    return render(request, "inventory/grn_edit.html", {
        "grn": grn,
        "items": items,
        "sub_items": sub_items,   # 🔥 ADD THIS
    })

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def grn_detail(request, grn_id):
    grn = get_object_or_404(GoodsReceiveNote, id=grn_id)
    items = grn.items.select_related(
        "product",
        "batch",
        "batch__batch"
    ).all()

    return render(request, "inventory/grn_detail.html", {
        "grn": grn,
        "items": items
    })



def _parse_int_or_none(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
    
from django.db.models.functions import Lower   # ✅ ADD THIS IMPORT
@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def products_stock_list_view(request):

    # -----------------------------
    # GET FILTER VALUES
    # -----------------------------
    search = request.GET.get('q') or None
    location_type = request.GET.get('location_type') or None
    location_id = _parse_int_or_none(request.GET.get('location_id'))
    batch_no = request.GET.get('batch_no') or None
    expiry_from = request.GET.get('expiry_from') or None
    expiry_to = request.GET.get('expiry_to') or None
    page = request.GET.get('page', 1)

    # NEW: Get sort parameter
    sort = request.GET.get('sort')  # 'asc', 'desc' or None/empty

    user = request.user
    role = getattr(user.userprofile, "role", None)

    # -----------------------------
    # ROLE BASED LOCATION FILTER
    # -----------------------------
    if role == "branch_manager":
        branch_id = BranchManager.objects.get(
            mobile_no=user.username
        ).branch.id

        location_type = "BRANCH"
        location_id = branch_id

    elif not location_type and role in ["admin", "HO_operation", "HO_manager"]:
        location_type = "HO"

    # -----------------------------
    # DESTINATION DROPDOWN DATA
    # -----------------------------
    if location_type:
        destination_qs = get_destination_queryset(location_type)
    else:
        destination_qs = []

    # -----------------------------
    # MAIN STOCK QUERY (ONLY SORT UPDATED)
    # -----------------------------
    qs = annotated_product_stock_qs(
        Product,
        location_type=location_type,
        location_id=location_id,
        search=search,
        batch_no=batch_no,
        expiry_from=expiry_from,
        expiry_to=expiry_to
    )

    # ────────────── FIX: Annotate closing_qty so we can sort on it ──────────────
    from django.db.models import F, ExpressionWrapper, DecimalField

    qs = qs.annotate(
        closing_qty=ExpressionWrapper(
            F('in_qty') - F('out_qty') - F('reserved_qty'),
            output_field=DecimalField(max_digits=15, decimal_places=3, null=True)
        )
    )
    # ───────────────────────────────────────────────────────────────────────────────

    # Dynamic sorting based on ?sort= parameter
    if sort == 'desc':
        qs = qs.order_by('-product_name')          # Z → A
    elif sort == 'asc':
        qs = qs.order_by(Lower('product_name'))    # A → Z
    elif sort == 'avail_desc':
        qs = qs.order_by('-closing_qty')           # Highest available first
    elif sort == 'avail_asc':
        qs = qs.order_by('closing_qty')            # Lowest available first
    else:
        qs = qs.order_by(Lower('product_name'))    # default A → Z (same as before)

    # -----------------------------
    # PAGINATION
    # -----------------------------
    paginator = Paginator(qs, 10)
    products_page = paginator.get_page(page)

    # -----------------------------
    # PREPARE TABLE DATA
    # -----------------------------
    rows = []

    for p in products_page:
        if (batch_no or expiry_from or expiry_to) and hasattr(p, 'batch_in_qty'):
            in_qty = getattr(p, 'batch_in_qty', Decimal('0'))
            out_qty = Decimal('0')
            reserved = Decimal('0')
        else:
            in_qty = getattr(p, 'in_qty', Decimal('0'))
            out_qty = getattr(p, 'out_qty', Decimal('0'))
            reserved = getattr(p, 'reserved_qty', Decimal('0'))

        closing = in_qty - out_qty - reserved

        rows.append({
            "id": p.pk,
            "name": getattr(p, 'product_name', str(p)),
            "in_qty": str(in_qty),
            "out_qty": str(out_qty),
            "reserved_qty": str(reserved),
            "closing_qty": str(closing),
        })

    # -----------------------------
    # PRESERVE FILTERS FOR PAGINATION
    # -----------------------------
    params = request.GET.copy()
    params.pop('page', None)

    
    from django.db.models import Sum, Q
    
    sub_item_qs = GoodsReceiveNoteSubItem.objects.select_related(
        "sub_item",
        "grn__purchase_order"
    )
    
    # -----------------------------
    # LOCATION FILTER (SAME AS PRODUCT)
    # -----------------------------
    if location_type and location_id:
        sub_item_qs = sub_item_qs.filter(
            grn__destination_type=location_type,
            grn__destination_id=location_id
        )
    
    # -----------------------------
    # SEARCH FILTER
    # -----------------------------
    if search:
        sub_item_qs = sub_item_qs.filter(
            sub_item__item_name__icontains=search
        )
    
    # -----------------------------
    # AGGREGATE
    # -----------------------------
    sub_item_qs = sub_item_qs.values(
        "sub_item__item_name"
    ).annotate(
        total_received=Sum("received_qty")
    )
    
    sub_item_rows = []
    
    for r in sub_item_qs:
        sub_item_rows.append({
            "name": r["sub_item__item_name"],
            "qty": r["total_received"] or 0
        })    

    context = {
        "rows": rows,
        "page_obj": products_page,
        "paginator": paginator,
        "base_qs": params.urlencode(),
        "sub_item_rows": sub_item_rows,
        "filters": {
            "location_type": location_type,
            
            "location_id": location_id,
            "q": search,
            "batch_no": batch_no,
            "expiry_from": expiry_from,
            "expiry_to": expiry_to,
            "sort": sort,                     # pass current sort to template
        },
        "destination_qs": destination_qs,
    }

    return render(request, "inventory/products_stock_list.html", context)

# stock export to excel
from openpyxl import Workbook

@login_required
@role_required(['admin', 'HO_operation', 'HO_manager', 'branch_manager'])
def export_products_stock_excel(request):
    search = request.GET.get('q') or None
    location_type = request.GET.get('location_type') or None
    location_id = _parse_int_or_none(request.GET.get('location_id'))

    batch_no = request.GET.get('batch_no') or None
    expiry_from = request.GET.get('expiry_from') or None
    expiry_to = request.GET.get('expiry_to') or None

    user = request.user
    role = getattr(user.userprofile, "role", None)

    # 🔐 ROLE BASED LOCATION FILTER
    if role == "branch_manager":
        branch_id = BranchManager.objects.get(
            mobile_no=user.username
        ).branch.id

        location_type = "BRANCH"
        location_id = branch_id

    # Fetch stock data (same as list view)
    qs = annotated_product_stock_qs(
        Product,
        location_type=location_type,
        location_id=location_id,
        search=search,
        batch_no=batch_no,
        expiry_from=expiry_from,
        expiry_to=expiry_to
    ).order_by('product_name')

    # 🟢 Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Product Stock"

    # 🟢 Excel Header
    headers = [
        "Product Name",
        "In Qty",
        "Out Qty",
        "Reserved Qty",
        "Closing Qty",
    ]
    ws.append(headers)

    # 🟢 Excel Rows
    for p in qs:
        if (batch_no or expiry_from or expiry_to) and hasattr(p, 'batch_in_qty'):
            in_qty = getattr(p, 'batch_in_qty', Decimal('0'))
            out_qty = Decimal('0')
            reserved = Decimal('0')
        else:
            in_qty = getattr(p, 'in_qty', Decimal('0'))
            out_qty = getattr(p, 'out_qty', Decimal('0'))
            reserved = getattr(p, 'reserved_qty', Decimal('0'))

        closing = in_qty - out_qty - reserved

        ws.append([
            getattr(p, 'product_name', str(p)),
            float(in_qty),
            float(out_qty),
            float(reserved),
            float(closing),
        ])

    # 🟢 Prepare HTTP response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="product_stock.xlsx"'

    wb.save(response)
    return response


# ---- batch api ------
def load_batches(request):
    product_id = request.GET.get("product_id")
    print("p id:",product_id)
    batches = ProductBatch.objects.filter(product_id=product_id)

    return JsonResponse({
        "results": [
            {"id": b.id, "name": str(b.batch)}
            for b in batches
        ]
    })

# -------------------- MTN ----------------
def fetch_mtn_available_qty(request):
    product_id = request.GET.get("product_id")
    batch_id = request.GET.get("batch_id")
    source_type = request.GET.get("source_type")
    source_id = request.GET.get("source_id")

    if not all([product_id, batch_id, source_type, source_id]):
        return JsonResponse({"available_qty": "0.000"})

    stock = CurrentStock.objects.filter(
        product_id=product_id,
        batch_id=batch_id,
        location_type=source_type,
        location_id=source_id
    ).first()

    available = stock.available_qty if stock else Decimal("0.000")

    return JsonResponse({
        "available_qty": str(available)
    })


@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def create_mtn(request):
    if request.method == "POST":
        source_type = request.POST.get("source_type")
        source_id = request.POST.get("source")
        destination_type = request.POST.get("destination_type")
        destination_id = request.POST.get("destination")
        status = request.POST.get("status")
        remarks = request.POST.get("remarks")
        transfer_date = request.POST.get("date") or timezone.now().date()

        products = request.POST.getlist("product[]")
        batches = request.POST.getlist("batch[]")
        qtys = request.POST.getlist("qty[]")
        item_remarks = request.POST.getlist("item_remarks[]")

        try:
            with transaction.atomic():

                # 1️⃣ Create MTN HEADER (always DRAFT first)
                mtn = MaterialTransferNote.objects.create(
                    source_type=source_type,
                    source_id=source_id,
                    destination_type=destination_type,
                    destination_id=destination_id,
                    transfer_date=transfer_date,
                    status="DRAFT",
                    remark=remarks,
                    created_by=request.user
                )

                # 2️⃣ Create MTN ITEMS (this triggers reservation)
                for i in range(len(products)):
                    if not products[i] or not qtys[i]:
                        continue

                    MTNItem.objects.create(
                        mtn=mtn,
                        product_id=products[i],
                        batch_id=batches[i],
                        transfer_qty=qtys[i],
                        remarks=item_remarks[i]
                    )

                # 3️⃣ If user selected APPROVED → update status
                if status == "APPROVED":
                    mtn.status = "APPROVED"
                    mtn.save()   # 🔥 triggers pre_save logic

                return redirect("mtn_list_view")

        except Exception as e:
            print("MTN ERROR:", e)

    products = Product.objects.all()
    return render(request, "inventory/mtn_form.html", {
        "products": products
    })


from crmapp.models import BranchManager

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def mtn_list_view(request):
    mtns = MaterialTransferNote.objects.all().order_by('-transfer_date')

    user = request.user.username

    # 🔐 ROLE BASED FILTER
    if request.user.userprofile.role == "branch_manager":
        branch_id = BranchManager.objects.get(mobile_no = user).branch.id
        mtns = mtns.filter(
            source_type="BRANCH",
            source_id=branch_id
        )
    
    elif request.user.userprofile.role == "admin":
        mtns = MaterialTransferNote.objects.all().order_by('-transfer_date')

    q = request.GET.get('q')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # 🔍 Search
    if q:
        mtns = mtns.filter(
            Q(mtn_no__icontains=q)
        )

    # 📅 Date filter
    if from_date:
        mtns = mtns.filter(transfer_date__gte=from_date)

    if to_date:
        mtns = mtns.filter(transfer_date__lte=to_date)

    # 📄 Pagination (10 per page)
    paginator = Paginator(mtns, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "mtns": page_obj,
        "page_obj": page_obj,
    }

    return render(request, "inventory/mtn_list.html", context)


@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def mtn_detail_view(request, pk):
    mtn = get_object_or_404(
        MaterialTransferNote.objects.prefetch_related(
            "items",
            "items__product",
            "items__batch",
            "items__batch__batch",
        ),
        pk=pk
    )

    context = {
        "mtn": mtn,
        "items": mtn.items.all(),
    }
    return render(request, "inventory/mtn_detail.html", context)

@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def mtn_edit_view(request, pk):
    mtn = get_object_or_404(MaterialTransferNote, pk=pk)

    # 🔒 Do not allow editing after approval
    if mtn.status != "DRAFT":
        return redirect("mtn_detail_view", pk=mtn.pk)

    if request.method == "POST":
        source_type = request.POST.get("source_type")
        source_id = request.POST.get("source")
        destination_type = request.POST.get("destination_type")
        destination_id = request.POST.get("destination")
        date = request.POST.get("date")
        status = request.POST.get("status")
        remarks = request.POST.get("remarks")

        products = request.POST.getlist("product[]")
        batches = request.POST.getlist("batch[]")
        qtys = request.POST.getlist("qty[]")
        item_remarks = request.POST.getlist("item_remarks[]")

        try:
            with transaction.atomic():

                # 1️⃣ Update MTN header
                mtn.source_type = source_type
                mtn.source_id = source_id
                mtn.destination_type = destination_type
                mtn.destination_id = destination_id
                mtn.transfer_date = date or timezone.now().date()
                mtn.remark = remarks
                mtn.save()

                # 2️⃣ Remove old items (IMPORTANT)
                # This will also release reserved stock
                mtn.items.all().delete()

                # 3️⃣ Re-create items (re-reserve stock)
                for i in range(len(products)):
                    if not products[i] or not qtys[i]:
                        continue

                    MTNItem.objects.create(
                        mtn=mtn,
                        product_id=products[i],
                        batch_id=batches[i],
                        transfer_qty=Decimal(qtys[i]),
                        remarks=item_remarks[i]
                    )

                # 4️⃣ Approve if selected
                if status == "APPROVED":
                    mtn.status = "APPROVED"
                    mtn.save()  # 🔥 triggers pre_save approval logic

                return redirect("mtn_list_view")

        except Exception as e:
            print("MTN EDIT ERROR:", e)

    # GET request → load form with existing data
    products = Product.objects.all()

    context = {
        "products": products,
        "mtn": mtn,
        "items": mtn.items.all(),
        "is_edit": True,
    }
    return render(request, "inventory/mtn_form.html", context)



# Material request note
def generate_request_no():
    today = timezone.now().strftime("%Y%m%d")
    prefix = f"REQ/{today}/"
    last = MaterialRequest.objects.filter(
        request_no__startswith=prefix
    ).order_by("-request_no").first()

    if last:
        last_no = int(last.request_no.split("/")[-1])
        new_no = last_no + 1
    else:
        new_no = 1

    return f"{prefix}{new_no:03d}"


@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
@transaction.atomic
def create_material_request(request):
    role = request.user.userprofile.role
    if role not in ["branch_manager"]:
          raise PermissionDenied("Only branch manager can raise request")

    branch = BranchManager.objects.get(
        mobile_no=request.user.username
    ).branch

    if request.method == "POST":
        mr = MaterialRequest.objects.create(
            request_no=generate_request_no(),
            source_type="BRANCH",
            source_id=branch.id,
            requested_by=request.user,
            status="SUBMITTED",
            remarks=request.POST.get("remarks")
        )

        products = request.POST.getlist("product_id[]")
        print("Products...", products)
        qtys = request.POST.getlist("qty[]")

        for p, q in zip(products, qtys):
            MaterialRequestItem.objects.create(
                material_request=mr,
                product_id=p,
                requested_qty=Decimal(q)
            )

        return redirect("material_request_list")
    products = Product.objects.all().order_by("product_name")
    return render(request, "inventory/material_request_create.html",  {
    "products": products,
})




@login_required
@role_required(['admin',"HO_operation","HO_manager","branch_manager"])
def material_request_list(request):
    role = request.user.userprofile.role

    # ---------------- BASE QUERYSET ----------------
    if role == "branch_manager":
        branch = BranchManager.objects.get(
            mobile_no=request.user.username
        ).branch

        qs = MaterialRequest.objects.filter(
            source_type="BRANCH",
            source_id=branch.id
        )
    else:
        qs = MaterialRequest.objects.all()
        branch = None

    # ---------------- FILTER PARAMS ----------------
    search = request.GET.get("search", "")
    branch_id = request.GET.get("branch", "")
    status = request.GET.get("status", "")

    if search:
        qs = qs.filter(request_no__icontains=search)

    if branch_id:
        qs = qs.filter(source_type="BRANCH", source_id=branch_id)

    if status:
        qs = qs.filter(status=status)

    qs = qs.order_by("-created_at")

    # ---------------- PAGINATION ----------------
    paginator = Paginator(qs, 10)   # 10 records per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    branches = Branch.objects.all()

    return render(
        request,
        "inventory/material_request_list.html",
        {
            "requests": page_obj,          # IMPORTANT
            "page_obj": page_obj,
            "branches": branches,
            "selected_search": search,
            "selected_branch": branch_id,
            "selected_status": status,
            "role":role,
        }
    )

@login_required
@transaction.atomic
def material_request_detail(request, pk):
    mr = get_object_or_404(MaterialRequest, pk=pk)
    role = request.user.userprofile.role

    # 🔐 Branch can only view their own requests
    if role == "branch_manager":
        branch = BranchManager.objects.get(
            mobile_no=request.user.username
        ).branch
        if mr.source_type != "BRANCH" or mr.source_id != branch.id:
            raise PermissionDenied()

    # 🔒 Prevent approving again
    is_editable = (
        role in ["admin", "HO_manager"]
        and mr.status == "SUBMITTED"
    )

    if request.method == "POST":
        if not is_editable:
            raise PermissionDenied()

        for item in mr.items.all():
            raw_val = request.POST.get(f"approved_qty_{item.id}")

            if raw_val in [None, ""]:
                item.approved_qty = item.requested_qty
            else:
                item.approved_qty = Decimal(raw_val)

            item.save()

        mr.status = "APPROVED"
        mr.save()

        return redirect("material_request_list")
    branch = Branch.objects.get(id = mr.source_id)
    req_user = User.objects.get(username = mr.requested_by).first_name
    return render(request, "inventory/material_request_detail.html", {
        "mr": mr,
        "branch":branch,
        "req_user":req_user,
        "items": mr.items.all(),
        "is_editable": is_editable,
    })

@transaction.atomic
def approve_material_request(request, pk):
    if request.user.userprofile.role not in ["admin", "HO_manager"]:
        raise PermissionDenied()

    mr = get_object_or_404(MaterialRequest, pk=pk)

    for item in mr.items.all():
        approved = request.POST.get(f"approved_qty_{item.id}")
        print('approved',approved)
        item.approved_qty = Decimal(approved)
        item.save()

    mr.status = "APPROVED"
    mr.save()

    return redirect("material_request_list")


def reject_material_request(request, pk):
    mr = get_object_or_404(MaterialRequest, pk=pk)
    mr.status = "REJECTED"
    mr.save()
    return redirect("material_request_list")



@login_required
def notification_read(request, pk):
    notification = get_object_or_404(
        Notification, pk=pk, user=request.user
    )
    notification.is_read = True
    notification.save()

    return redirect(
        "material_request_detail",
        pk=notification.related_request.id
    )


def notification_context(request):
    if request.user.is_authenticated:
        unread_count = request.user.notifications.filter(is_read=False).count()
        return {
            "unread_notification_count": unread_count
        }
    return {
        "unread_notification_count": 0
    }





@login_required
@role_required(['admin', 'HO_operation', 'HO_manager'])
@transaction.atomic
def create_dc_from_mtn(request, mtn_id):
    mtn = get_object_or_404(MaterialTransferNote, id=mtn_id)

    # 🚫 Only approved MTN allowed
    if mtn.status != "APPROVED":
        messages.error(request, "MTN must be approved before creating Delivery Challan.")
        return redirect("mtn_detail_view", pk=mtn.id)

    # 🚫 Prevent duplicate DC
    if hasattr(mtn, "delivery_challan"):
        messages.warning(request, "Delivery Challan already created for this MTN.")
        return redirect("mtn_detail_view", pk=mtn.id)

    mtn_items = mtn.items.select_related("product", "batch")

    if request.method == "POST":
        delivery_date = request.POST.get("delivery_date") or timezone.now().date()
        remarks = request.POST.get("remarks")

        # 1️⃣ Create DC HEADER
        dc = DeliveryChallan.objects.create(
            mtn=mtn,
            source_type=mtn.source_type,
            source_id=mtn.source_id,
            destination_type=mtn.destination_type,
            destination_id=mtn.destination_id,
            delivery_date=delivery_date,
            remarks=remarks,
            status="DISPATCHED",
            created_by=request.user,
            delivery_partner_name = request.POST.get("delivery_partner_name"),
            delivery_person_name = request.POST.get("delivery_person_name"),
            delivery_person_phone = request.POST.get("delivery_person_phone"),

        )

        # 2️⃣ Create DC ITEMS (copy from MTN)
        for item in mtn_items:
            DeliveryChallanItem.objects.create(
                delivery_challan=dc,
                product=item.product,
                batch=item.batch,
                quantity=item.transfer_qty,
                remarks=item.remarks
            )

            # 3️⃣ FINAL STOCK OUT
            stock = CurrentStock.objects.select_for_update().get(
                product=item.product,
                batch=item.batch,
                location_type=mtn.source_type,
                location_id=mtn.source_id
            )

            stock.out_qty += item.transfer_qty
            stock.reserved_qty -= item.transfer_qty
            stock.recompute_closing()

            StockLedger.objects.create(
                product=item.product,
                batch=item.batch,
                location_type=mtn.source_type,
                location_id=mtn.source_id,
                transaction_type="MTN_OUT",
                transaction_ref=dc.dc_no,
                document_id=dc.id,
                out_qty=item.transfer_qty,
                balance_qty=stock.closing_qty,
                created_by=request.user,
                remarks="Delivery Challan Dispatch",
                

            )

        messages.success(request, f"Delivery Challan {dc.dc_no} created successfully.")
        return redirect("mtn_detail_view", pk=mtn.id)

    return render(request, "inventory/delivery_challan_create.html", {
        "mtn": mtn,
        "items": mtn_items,
    })


from .utils import get_destination_details

@login_required
@role_required(['admin', 'HO_operation', 'HO_manager', 'branch_manager'])
def dc_detail_view(request, pk):
    dc = get_object_or_404(
        DeliveryChallan.objects.select_related("mtn").prefetch_related(
            "items",
            "items__product",
            "items__batch",
            "items__batch__batch",
        ),
        pk=pk
    )

    source = get_destination_details(dc.source_type, dc.source_id)
    destination = get_destination_details(dc.destination_type, dc.destination_id)

    return render(
        request,
        "inventory/delivery_challan_detail.html",
        {
            "dc": dc,
            "items": dc.items.all(),
            "source": source,
            "destination": destination,
        }
    )




@login_required
@role_required(['admin', 'HO_operation', 'HO_manager', 'branch_manager'])
def dc_list_view(request):
    qs = DeliveryChallan.objects.select_related(
        "mtn"
    ).order_by("-created_at")

    user = request.user.username
    role = request.user.userprofile.role

    # 🔐 ROLE BASED FILTER
    if role == "branch_manager":
        branch_id = BranchManager.objects.get(
            mobile_no=user
        ).branch.id

        qs = qs.filter(
            source_type="BRANCH",
            source_id=branch_id
        )

    # 🔍 SEARCH
    search = request.GET.get("search", "")
    if search:
        qs = qs.filter(
            Q(dc_no__icontains=search) |
            Q(mtn__mtn_no__icontains=search)
        )

    # 📅 DATE FILTER
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")

    if from_date:
        qs = qs.filter(delivery_date__gte=from_date)
    if to_date:
        qs = qs.filter(delivery_date__lte=to_date)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    for dc in page_obj:
        src = get_destination_object(dc.source_type, dc.source_id)
        dst = get_destination_object(dc.destination_type, dc.destination_id)

        dc.source_name = str(src) if src else "-"
        dc.destination_name = str(dst) if dst else "-"


    return render(
        request,
        "inventory/delivery_challan_list.html",
        {
            "dcs": page_obj,
            "page_obj": page_obj,
            "querystring": request.GET.urlencode(),
        }
    )



@login_required
@role_required(['admin', 'HO_operation', 'HO_manager'])
def dc_edit_view(request, pk):
    dc = get_object_or_404(DeliveryChallan, pk=pk)

    if request.method == "POST":
        dc.delivery_partner_name = request.POST.get("delivery_partner_name")
        dc.delivery_person_name = request.POST.get("delivery_person_name")
        dc.delivery_person_phone = request.POST.get("delivery_person_phone")
        dc.remarks = request.POST.get("remarks")

        dc.save(update_fields=[
            "delivery_partner_name",
            "delivery_person_name",
            "delivery_person_phone",
            "remarks",
        ])

        messages.success(request, "Delivery Challan updated successfully.")
        return redirect("dc_detail_view", pk=dc.pk)

    return render(
        request,
        "inventory/delivery_challan_edit.html",
        {
            "dc": dc
        }
    )


from django.http import HttpResponse
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from weasyprint import HTML

from .models import DeliveryChallan
from .utils import get_destination_details


@login_required
def dc_pdf_view(request, pk):
    # Get challan
    dc = get_object_or_404(DeliveryChallan, pk=pk)

    # Get source & destination
    source = get_destination_details(dc.source_type, dc.source_id)
    destination = get_destination_details(dc.destination_type, dc.destination_id)

    # Render HTML
    html_string = render_to_string(
        "inventory/delivery_challan_detail.html",
        {
            "dc": dc,
            "items": dc.items.all(),
            "source": source,
            "destination": destination,
        }
    )

    # Generate PDF (IMPORTANT: base_url)
    pdf_file = HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')
    ).write_pdf()

    # Response
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="DC_{dc.dc_no}.pdf"'

    return response