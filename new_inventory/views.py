from django.shortcuts import render, HttpResponse
from django.http import JsonResponse
from crmapp.models import UserProfile
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
    dest_obj = get_destination_object(po.destination_type, po.destination_id)
    dest_label = str(dest_obj) if dest_obj else ""
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
        "destination_initial": {"id": po.destination_id, "label": dest_label}
    })


# ------------------ Purchase Order Delete ---------------------

@login_required
def purchase_order_delete(request, id):
    po = get_object_or_404(PurchaseOrder, id=id)
    po.delete()
    return redirect("purchase_order_list")



#---------------------PDF------------------------



# @login_required
# def purchase_order_pdf(request, id):
#     from num2words import num2words   # convert amount into words

#     po = get_object_or_404(PurchaseOrder, id=id)
#     items = PurchaseOrderItem.objects.filter(purchase_order=po)

#     # -------------------------
#     # CALCULATE ITEM AMOUNTS
#     # -------------------------
#     total_amount = 0
#     item_data = []

#     for item in items:
#         qty = float(item.quantity or 0)
#         rate = float(item.rate or 0)
#         discount = float(item.discount or 0)

#         # Calculate amount
#         amount = qty * rate

#         if discount > 0:
#             amount = amount - (amount * discount / 100)

#         total_amount += amount

#         item_data.append({
#             "product": item.product,
#             "quantity": item.quantity,
#             "rate": item.rate,
#             "discount": item.discount,
#             "remarks": item.remarks,
#             "amount": round(amount, 2),
#         })

#     # -------------------------
#     # GRAND TOTAL
#     # -------------------------
#     freight = float(po.freight_charges or 0)
#     grand_total = total_amount + freight

#     # -------------------------
#     # TOTAL IN WORDS
#     # -------------------------
#     amount_words = num2words(grand_total, to='currency', lang='en_IN').title()

#     # -------------------------
#     # CONTEXT TO TEMPLATE
#     # -------------------------
#     context = {
#         "po": po,
#         "items": item_data,
#         "total_amount": round(total_amount, 2),
#         "freight_charges": freight,
#         "grand_total": round(grand_total, 2),
#         "total_amount_in_words": amount_words,
#     }

#     # -------------------------
#     # RENDER PDF
#     # -------------------------
#     template = get_template('inventory/purchase_order_pdf.html')
#     html = template.render(context)

#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'attachment; filename="PO_{po.po_no}.pdf"'

#     pisa_status = pisa.CreatePDF(html, dest=response)

#     if pisa_status.err:
#         return HttpResponse("Error generating PDF")

#     return response

@login_required
def purchase_order_pdf(request, id):
    """
    Render PO PDF. Use ?download=1 to force download (attachment).
    Without ?download=1 the PDF will be served inline so the browser can open it.
    """
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
    # num2words sometimes expects ints; but it supports floats for currency mode.
    try:
        amount_words = num2words(grand_total, to='currency', lang='en_IN').title()
    except Exception:
        # fallback to simple words for whole rupees
        amount_words = num2words(int(round(grand_total)), lang='en_IN').title()

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

# @login_required
# def grn_create(request, po_id):
#     po = get_object_or_404(PurchaseOrder, id=po_id)
#     po_items = po.items.all()  # adjust relation name

#     # --- compute remaining for each PO item (already-received across previous GRNs) ---
#     remaining_by_item = {}
#     for pi in po_items:
#         s = GoodsReceiveNoteItem.objects.filter(po_item=pi).aggregate(total=Sum("received_qty"))["total"]
#         already = Decimal(s or 0)
#         remaining = Decimal(pi.quantity or 0) - already
#         if remaining < 0:
#             remaining = Decimal("0.00")
#         remaining_by_item[pi.id] = remaining

#     for pi in po_items:
#         pi.remaining = remaining_by_item.get(pi.id, Decimal("0.00"))
#     # existing destination handling...
#     po_dest_type = getattr(po, "destination_type", None)
#     po_dest_id   = getattr(po, "destination_id", None)
#     dest_obj = get_destination_object(po_dest_type, po_dest_id)
#     dest_label = str(dest_obj) if dest_obj else ""

#     if request.method == "POST":
#         form = GRNForm(request.POST)
#         if form.is_valid():
#             # SERVER-SIDE: re-check remaining before creating (important)
#             any_created = False
#             errors = []
#             for pi in po_items:
#                 raw = request.POST.get(f"received_qty_{pi.id}", "").strip()
#                 if raw in ("", None, ""):
#                     continue
#                 try:
#                     received_qty = Decimal(raw)
#                 except Exception:
#                     errors.append(f"Invalid quantity for {pi.product.product_name}.")
#                     continue

#                 if received_qty <= 0:
#                     continue

#                 # re-check remaining from DB (safer than trusting the earlier variable)
#                 s = GoodsReceiveNoteItem.objects.filter(po_item=pi).aggregate(total=Sum("received_qty"))["total"]
#                 already_db = Decimal(s or 0)
#                 remaining_db = Decimal(pi.quantity or 0) - already_db
#                 if remaining_db <= 0:
#                     errors.append(f"{pi.product.product_name} is already fully received.")
#                     continue
#                 if received_qty > remaining_db:
#                     errors.append(
#                         f"Received qty for {pi.product.product_name} exceeds remaining ({remaining_db})."
#                     )
#                     continue

#                 # if passes, create below after saving grn
#             if errors:
#                 from django.contrib import messages
#                 for e in errors:
#                     messages.error(request, e)
#             else:
#                 # proceed to create GRN and items (your existing logic)
#                 grn = form.save(commit=False)
#                 grn.purchase_order = po
#                 grn.vendor = po.vendor
#                 grn.created_by = request.user
#                 grn.destination_type = form.cleaned_data["destination_type"]
#                 grn.destination_id = form.cleaned_data["destination_id"]
#                 grn.save()

#                 items_created = 0
#                 for pi in po_items:
#                     raw = request.POST.get(f"received_qty_{pi.id}", "").strip()
#                     if raw in ("", None, ""):
#                         continue
#                     received_qty = Decimal(raw)
#                     if received_qty <= 0:
#                         continue

#                     remarks = request.POST.get(f"remarks_{pi.id}", "")[:255]

#                     GoodsReceiveNoteItem.objects.create(
#                         grn=grn,
#                         po_item=pi,
#                         product=pi.product,
#                         ordered_qty=pi.quantity,
#                         received_qty=received_qty,
#                         remarks=remarks
#                     )
#                     items_created += 1

#                 # update PO status (your logic)
#                 all_received = sum(i.received_qty for i in grn.items.all())
#                 all_ordered  = sum(i.ordered_qty  for i in grn.items.all())
#                 po.status = "CLOSED" if all_received >= all_ordered else "PARTIALLY_RECEIVED"
#                 po.save()
#                 return redirect("grn_list")
#     else:
#         form = GRNForm(initial={
#             "destination_type": po_dest_type,
#             "destination_id": po_dest_id
#         })

#     return render(request, "inventory/grn_create.html", {
#         "form": form,
#         "po": po,
#         "po_items": po_items,
#         "destination_initial": {"id": po_dest_id, "label": dest_label},
#         "remaining_by_item": remaining_by_item,
#     })



@login_required
def grn_create(request, po_id):
    po = get_object_or_404(PurchaseOrder, id=po_id)
    po_items = po.items.all()

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

                        if items_created == 0:
                            # nothing created — rollback by raising
                            raise ValueError("No GRN items were created.")

                        # Recompute PO item remaining from DB to decide PO status
                        all_done = True
                        for pi in po_items:
                            s2 = GoodsReceiveNoteItem.objects.filter(po_item=pi).aggregate(total=Sum("received_qty"))["total"]
                            already2 = Decimal(s2 or 0)
                            remaining2 = Decimal(pi.quantity or 0) - already2
                            if remaining2 > 0:
                                all_done = False
                                break

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
        "destination_initial": {"id": po_dest_id, "label": dest_label},
        "remaining_by_item": remaining_by_item,
    })


# def grn_list(request):
#     grns = GoodsReceiveNote.objects.all().order_by("-created_at")
#     return render(request, "inventory/grn_list.html", {"grns": grns})



def grn_list(request):
    """
    List GRNs with:
      - search: request.GET['search'] (matches PO no, PO id, vendor name, vendor mobile)
      - date filter: from_date / to_date (YYYY-MM-DD)
      - pagination: ?page=...
    Returns:
      - grns: the page's object list (used by your template loop)
      - page_obj: the Paginator page object (used by your pagination UI)
      - querystring: serialized GET params except 'page' (so pagination links preserve filters)
    """
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
def grn_detail(request, grn_id):
    grn = get_object_or_404(GoodsReceiveNote, id=grn_id)
    items = grn.items.all()
    return render(request, "inventory/grn_detail.html", {"grn": grn, "items": items})
