from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from .models import Vendor, PurchaseOrder, PurchaseOrderItem, Site, HO
from crmapp.models import UserProfile
from .forms import *
from .utils import get_destination_queryset
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required

# ------- load destination --------
def load_destinations(request):
    dest_type = request.GET.get("destination_type")
    qs = get_destination_queryset(dest_type)

    data = [{"id": obj.id, "name": str(obj)} for obj in qs]
    return JsonResponse({"results": data})


# ------------ Vendor Section start here ----------
def vendor_add(request):
    if request.method == "POST":
        form = VendorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("vendor_list")
    else:
        form = VendorForm()
    return render(request, 'inventory/add_vendor.html', {'form': form})


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
        vendors = vendors.filter(compony_type=company_type)

    if supplier_category:
        vendors = vendors.filter(supplier_category=supplier_category)

    company_types = Vendor.objects.values_list("compony_type", flat=True).distinct()
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


# ----------------------- Head Office staff section ------------------------
UserModel = get_user_model()

def add_ho_staff(request):
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

    return render(request, "inventory/add_ho.html", {"form": form})


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


def ho_delete(request, pk):
    ho = get_object_or_404(HO, id=pk)
    ho.delete()
    return redirect('ho_list')


# ----------------- Site section -----------------------
def add_site(request):
    if request.method == "POST":
        form = SiteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("site_list")
    else:
        form = SiteForm()

    return render(request, "inventory/add_site.html", {"form": form})


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


def site_edit(request, id):
    site = get_object_or_404(Site, id=id)
    form = SiteForm(request.POST or None, instance=site)

    if form.is_valid():
        form.save()
        return redirect("site_list")

    return render(request, "inventory/add_site.html", {"form": form, "site": site})


def site_delete(request, id):
    site = get_object_or_404(Site, id=id)
    site.delete()
    return redirect("site_list")


# ------------------ Purchase order section --------------- 
@login_required
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
    })



# ------------------ Purchase order list ---------------------

@login_required
def purchase_order_list(request):
    search = request.GET.get("search", "")
    destination_type = request.GET.get("destination_type", "")
    status = request.GET.get("status", "")
    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")

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
def purchase_order_edit(request, id):
    po = get_object_or_404(PurchaseOrder, id=id)

    if request.method == "POST":
        form = PurchaseOrderForm(request.POST, request.FILES, instance=po)
        formset = PurchaseOrderItemFormSet(request.POST, instance=po, prefix="items")

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            return redirect("purchase_order_list")

    else:
        form = PurchaseOrderForm(instance=po)
        formset = PurchaseOrderItemFormSet(instance=po, prefix="items")

    return render(request, "inventory/purchase_order_edit.html", {
        "form": form,
        "formset": formset,
        "po": po,
    })


# ------------------ Purchase Order Delete ---------------------

@login_required
def purchase_order_delete(request, id):
    po = get_object_or_404(PurchaseOrder, id=id)
    po.delete()
    return redirect("purchase_order_list")



#---------------------PDF------------------------

from django.template.loader import get_template
from xhtml2pdf import pisa
from django.http import HttpResponse

@login_required
def purchase_order_pdf(request, id):
    from num2words import num2words   # convert amount into words

    po = get_object_or_404(PurchaseOrder, id=id)
    items = PurchaseOrderItem.objects.filter(purchase_order=po)

    # -------------------------
    # CALCULATE ITEM AMOUNTS
    # -------------------------
    total_amount = 0
    item_data = []

    for item in items:
        qty = float(item.quantity or 0)
        rate = float(item.rate or 0)
        discount = float(item.discount or 0)

        # Calculate amount
        amount = qty * rate

        if discount > 0:
            amount = amount - (amount * discount / 100)

        total_amount += amount

        item_data.append({
            "product": item.product,
            "quantity": item.quantity,
            "rate": item.rate,
            "discount": item.discount,
            "remarks": item.remarks,
            "amount": round(amount, 2),
        })

    # -------------------------
    # GRAND TOTAL
    # -------------------------
    freight = float(po.freight_charges or 0)
    grand_total = total_amount + freight

    # -------------------------
    # TOTAL IN WORDS
    # -------------------------
    amount_words = num2words(grand_total, to='currency', lang='en_IN').title()

    # -------------------------
    # CONTEXT TO TEMPLATE
    # -------------------------
    context = {
        "po": po,
        "items": item_data,
        "total_amount": round(total_amount, 2),
        "freight_charges": freight,
        "grand_total": round(grand_total, 2),
        "total_amount_in_words": amount_words,
    }

    # -------------------------
    # RENDER PDF
    # -------------------------
    template = get_template('inventory/purchase_order_pdf.html')
    html = template.render(context)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="PO_{po.po_no}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)

    if pisa_status.err:
        return HttpResponse("Error generating PDF")

    return response



#----------------------------------GRN------------------------------------


from .models import GoodsReceiveNote, GoodsReceiveNoteItem


@login_required
def grn_create(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    po_items = po.items.all()

    if request.method == "POST":
        form = GRNForm(request.POST)

        if form.is_valid():
            grn = form.save(commit=False)
            grn.purchase_order = po
            grn.vendor = po.vendor
            grn.created_by = request.user
            grn.save()

            # Save GRN items
            for item in po_items:
                received_qty = request.POST.get(f"received_qty_{item.id}", 0)

                GoodsReceiveNoteItem.objects.create(
                    grn=grn,
                    po_item=item,
                    product=item.product,
                    ordered_qty=item.quantity,
                    received_qty=received_qty,
                    remarks=request.POST.get(f"remarks_{item.id}", "")
                )

            # Update PO Status
            total_received = sum(float(i.received_qty) for i in grn.items.all())
            total_ordered = sum(float(i.ordered_qty) for i in grn.items.all())

            if total_received >= total_ordered:
                po.status = "CLOSED"
            else:
                po.status = "PARTIALLY_RECEIVED"

            po.save()

            return redirect("grn_list")

    else:
        form = GRNForm()

    return render(request, "inventory/grn_create.html", {
        "form": form,
        "po": po,
        "po_items": po_items
    })



@login_required
def grn_list(request):
    grns = GoodsReceiveNote.objects.all().order_by("-created_at")
    return render(request, "inventory/grn_list.html", {"grns": grns})



@login_required
def grn_detail(request, grn_id):
    grn = get_object_or_404(GoodsReceiveNote, id=grn_id)
    items = grn.items.all()
    return render(request, "inventory/grn_detail.html", {"grn": grn, "items": items})
