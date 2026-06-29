from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from crmapp.models import TechnicianProfile
from crmapp.models import TechWorkList
from .models import AMCContract, AMCServiceVisit, AMCServiceSchedule






from .models import (
    AMCContract,
    AMCServiceVisit,
    AMCServiceSchedule
)
from .forms import (
    AMCContractForm,
    AMCServiceVisitForm
)
from crmapp.models import (
    service_management,
    WorkAllocation
)



# -------------------------------------------------------------------
# AJAX — LOAD SERVICES BASED ON CUSTOMER
# -------------------------------------------------------------------
@login_required
def load_services(request):
    customer_id = request.GET.get("customer_id")

    if not customer_id:
        return JsonResponse([], safe=False)

    services = service_management.objects.filter(
        customer_id=customer_id
    ).exclude(
        service_subject__startswith="AMC Visit"
    ).values(
        "id", "service_subject"
    )

    return JsonResponse(list(services), safe=False)




# -------------------------------------------------------------------
# AJAX — LOAD SERVICE DETAILS (TECHNICIANS FROM WORK ALLOCATION)
# -------------------------------------------------------------------
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required

from crmapp.models import service_management, ServiceProductFrequency, WorkAllocation


@login_required
def load_service_details(request):
    service_id = request.GET.get("service_id")

    if not service_id:
        return JsonResponse({"error": "Missing service_id"}, status=400)

    service = get_object_or_404(service_management, id=service_id)

    # 🔹 technicians
    techs = set()
    for w in WorkAllocation.objects.filter(service=service):
        techs.update(w.technician.all())

    # 🔥 PRODUCT FREQUENCY
    product_data = []
    frequencies = ServiceProductFrequency.objects.filter(service=service)

    for f in frequencies:
        product_data.append({
            "product_id": f.product.pk,
            "product_name": f.product.product_name,
            "frequency": f.remarks if f.remarks else str(f.frequency),
        })

    return JsonResponse({
        "branch_id": service.branch.id if service.branch else None,
        "technicians": [{"id": t.id, "name": str(t)} for t in techs],
        "start_candidate": service.service_date.isoformat() if service.service_date else None,
        "products": product_data
    })
# -------------------------------------------------------------------
# CREATE AMC CONTRACT
# -------------------------------------------------------------------
@login_required
def amc_create(request):

    if request.method == "POST":
        form = AMCContractForm(request.POST)

        customer_id = request.POST.get("customer")
        if customer_id:
            form.fields["service"].queryset = service_management.objects.filter(
                customer_id=customer_id
            ).exclude(
                service_subject__startswith="AMC Visit"
            )

        if form.is_valid():
            amc = form.save(commit=False)
            service_obj = form.cleaned_data["service"]

            # FIX 1: Pull frequency from cleaned form data and set explicitly
            amc.frequency = form.cleaned_data.get("frequency") or None

            # FIX 2: Guard against service having no service_date (avoids crash in generate_schedule)
            from datetime import date as _date
            amc.start_date = service_obj.service_date or _date.today()

            amc.branch = service_obj.branch
            amc.created_by = request.user
            amc.save()

            messages.success(request, "AMC created successfully")
            return redirect("amc:list")

        else:
            # Re-render form with validation errors
            return render(request, "amc/form.html", {
                "form": form,
                "title": "Create AMC"
            })

    else:
        form = AMCContractForm()

    return render(request, "amc/form.html", {
        "form": form,
        "title": "Create AMC"
    })

# -------------------------------------------------------------------
# AMC LIST
# -------------------------------------------------------------------
from django.core.paginator import Paginator
from datetime import date
from crmapp.models import ServiceProductFrequency   # ✅ ADD THIS

@login_required
def amc_detail(request, pk):
    amc = get_object_or_404(AMCContract, pk=pk)

    # ------------------------------------------------
    # HANDLE "ALLOCATE WORK" BUTTON (NO NEW PAGE)
    # ------------------------------------------------
    if request.method == "POST" and request.POST.get("allocate_visit_id"):
        visit_id = request.POST.get("allocate_visit_id")
        visit = get_object_or_404(AMCServiceVisit, id=visit_id, amc=amc)

        if visit.allocation_status == "ALLOCATED":
            messages.warning(request, "Work already allocated.")
            return redirect("amc:detail", amc.id)

        technicians = visit.technicians.all()

        schedule = AMCServiceSchedule.objects.filter(
            amc=amc,
            service_date=visit.service_date
        ).first()

        if not schedule or not schedule.is_approved:
            messages.warning(request, "AMC service is not approved.")
            return redirect("amc:detail", amc.id)

        service = service_management.objects.create(
            customer=amc.customer,
            branch=amc.branch,
            service_subject=f"AMC Visit - {visit.service_date}",
            service_date=visit.service_date,
            contract_type="AMC",
            gps_location=amc.default_gps_location,
            is_approved=schedule.is_approved
        )

        work = WorkAllocation.objects.create(
            service=service,
            customer_contact=(
                amc.default_customer_contact
                or amc.customer.primarycontact
            ),
            customer_address=(
                amc.default_customer_address
                or amc.customer.shifttopartyaddress
            ),
            payment_amount=(
                amc.default_payment_amount
                or amc.per_visit_amount
                or 0
            ),
            customer_payment_status=(
                amc.default_payment_status
                or "Pending"
            ),
            work_description=(
                amc.default_work_description
                or "AMC Scheduled Service"
            ),
        )

        work.technician.set(technicians)

        for tech in technicians:
            tech_work = TechWorkList.objects.create(
                technician=tech.user,
                service=service,
                status="Pending"
            )
            tech_work.work.add(work)

        visit.crm_service = service
        visit.crm_service_created_at = timezone.now()
        visit.allocation_status = "ALLOCATED"
        visit.save(update_fields=[
            "crm_service",
            "crm_service_created_at",
            "allocation_status"
        ])

        messages.success(request, "Work allocated successfully.")
        return redirect("amc:detail", amc.id)

    # ------------------------------------------------
    # NORMAL PAGE LOAD (GET)
    # ------------------------------------------------
    visits = (
        AMCServiceVisit.objects
        .filter(amc=amc)
        .order_by("service_date")
        .prefetch_related("technicians")
    )

    # 🔥 NEW: PRODUCT FREQUENCY FETCH
    product_freq = ServiceProductFrequency.objects.filter(
        service=amc.service
    )

    allocated_services = set(
        WorkAllocation.objects.values_list("service_id", flat=True)
    )

    return render(request, "amc/detail.html", {
        "amc": amc,
        "visits": visits,
        "allocated_services": allocated_services,
        "product_freq": product_freq   # ✅ ADD THIS
    })

# -------------------------------------------------------------------
# EDIT AMC
# -------------------------------------------------------------------
@login_required
def amc_edit(request, pk):
    amc = get_object_or_404(AMCContract, pk=pk)

    if request.method == "POST":
        form = AMCContractForm(request.POST, instance=amc)

        if form.is_valid():
            form.save()
            messages.success(request, "AMC updated successfully")
            return redirect("amc:detail", pk=amc.pk)

    else:
        form = AMCContractForm(instance=amc)
        form.fields["customer"].disabled = True
        form.fields["service"].disabled = True
        form.fields["start_date"].disabled = True
        form.fields["frequency"].disabled = True

    return render(request, "amc/form.html", {
        "form": form,
        "title": "Edit AMC"
    })

# -------------------------------------------------------------------
# CANCEL AMC
# -------------------------------------------------------------------
@login_required
def amc_delete(request, pk):
    amc = get_object_or_404(AMCContract, pk=pk)

    if request.method == "POST":
        amc.status = "Cancelled"
        amc.is_active = False
        amc.save()
        messages.success(request, "AMC Cancelled")
        return redirect("amc:list")

    return render(request, "amc/confirm_delete.html", {"amc": amc})





# -------------------------------------------------------------------
# AMC RENEWAL — CUSTOMER RESPONSE FROM EMAIL
# -------------------------------------------------------------------
def renew_yes(request, contract_number):
    """
    Customer clicked YES in email.
    Marks AMC as renewal requested.
    """

    amc = get_object_or_404(
        AMCContract,
        contract_number=contract_number
    )

    # ❌ If already expired
    if not amc.is_active:
        return render(request, "amc/renew_response.html", {
            "message": "This AMC is already expired."
        })

    # ❌ Prevent duplicate requests
    if amc.renewal_status in ["REQUESTED", "APPROVED"]:
        return render(request, "amc/renew_response.html", {
            "message": "Renewal request already submitted."
        })

    # ✅ Mark renewal requested
    amc.renewal_status = "REQUESTED"
    amc.renewal_requested_at = timezone.now()
    amc.save(update_fields=["renewal_status", "renewal_requested_at"])

    return render(request, "amc/renew_response.html", {
        "message": (
            "Thank you! Your AMC renewal request has been sent to admin. "
            "Our team will contact you after verification."
        )
    })






def renew_no(request, contract_number):
    """
    Customer clicked NO in email.
    AMC continues till expiry but will NOT be renewed.
    """

    amc = get_object_or_404(
        AMCContract,
        contract_number=contract_number
    )

    # ❌ If AMC already expired
    if not amc.is_active:
        return render(request, "amc/renew_response.html", {
            "message": "This AMC has already expired."
        })

    # ❌ Prevent repeat clicks
    if amc.renewal_status in ["APPROVED", "REJECTED", "NOT_RENEWED"]:
        return render(request, "amc/renew_response.html", {
            "message": "Your response has already been recorded."
        })

    # ✅ Mark as not renewing (DO NOT expire AMC)
    amc.renewal_status = "NOT_RENEWED"
    amc.save(update_fields=["renewal_status"])

    return render(request, "amc/renew_response.html", {
        "message": (
            "Thank you. Your AMC will continue till its expiry date "
            "but will not be renewed."
        )
    })


from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from .models import AMCContract

@staff_member_required
def renewal_requests(request):
    amcs = AMCContract.objects.filter(
        renewal_status="REQUESTED"
    ).order_by("end_date")

    return render(
        request,
        "amc/renewal_requests.html",
        {"amcs": amcs}
    )





from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from .models import AMCContract, AMCServiceVisit

@staff_member_required
def amc_service_visits(request, amc_id):
    amc = get_object_or_404(AMCContract, id=amc_id)

    visits = AMCServiceVisit.objects.filter(
        amc=amc
    ).order_by("service_date")

    return render(
        request,
        "amc/service_visits.html",
        {
            "amc": amc,
            "visits": visits
        }
    )






# -------------------------------------------------------------------
# AMC DASHBOARD (ACTUAL UI - NOT DJANGO ADMIN)
# -------------------------------------------------------------------


@login_required
def amc_dashboard(request):
    today = timezone.now().date()
    next_15_days = today + timedelta(days=15)

    total_amcs = AMCContract.objects.count()
    active_amcs = AMCContract.objects.filter(is_active=True).count()
    renewal_requests = AMCContract.objects.filter(
        renewal_status="REQUESTED"
    ).count()

    expiring_soon = AMCContract.objects.filter(
        is_active=True,
        end_date__lte=next_15_days
    ).count()

    expiring_amcs = AMCContract.objects.filter(
        is_active=True,
        end_date__range=(today, next_15_days)
    ).order_by("end_date")

    upcoming_services = AMCServiceVisit.objects.filter(
        service_date__range=(today, next_15_days)
    ).select_related("amc", "amc__customer", "amc__branch")


    return render(
        request,
        "amc/dashboard.html",
        {
            "total_amcs": total_amcs,
            "active_amcs": active_amcs,
            "renewal_requests": renewal_requests,
            "expiring_soon": expiring_soon,
            "expiring_amcs": expiring_amcs,
            "upcoming_services": upcoming_services,  # ✅ ADD THIS
        }
    )




# -------------------------------------------------------------------
# CALENDAR EVENTS
# -------------------------------------------------------------------
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import AMCContract, AMCServiceVisit, AMCServiceSchedule
@login_required
def amc_calendar_events(request):
    events = []

    # 🔵 ACTUAL SERVICE VISITS
    visits = AMCServiceVisit.objects.select_related(
        "amc", "amc__customer", "amc__branch"
    )

    for visit in visits:
        events.append({
            "title": f"Service Visit | {str(visit.amc.customer)}",
            "start": visit.service_date.isoformat(),
            "backgroundColor": "#0d6efd",
            "borderColor": "#0d6efd",
            "extendedProps": {
                "type": "Service Visit",
                "contract": visit.amc.contract_number,
                "customer": str(visit.amc.customer),
                "branch": visit.amc.branch.branch_name if visit.amc.branch else "-",
                "date": visit.service_date.strftime("%d %b %Y"),
            }
        })

    # 🟡 PLANNED SERVICE SCHEDULES
    schedules = AMCServiceSchedule.objects.select_related(
        "amc", "amc__customer", "amc__branch"
    ).filter(is_completed=False)

    for sch in schedules:
        events.append({
            "title": f"Scheduled Service | {str(sch.amc.customer)}",
            "start": sch.service_date.isoformat(),
            "backgroundColor": "#ffc107",
            "borderColor": "#ffc107",
            "extendedProps": {
                "type": "Scheduled Service",
                "contract": sch.amc.contract_number,
                "customer": str(sch.amc.customer),
                "branch": sch.amc.branch.branch_name if sch.amc.branch else "-",
                "date": sch.service_date.strftime("%d %b %Y"),
            }
        })

    # 🔴 AMC EXPIRY
    amcs = AMCContract.objects.filter(is_active=True)

    for amc in amcs:
        events.append({
            "title": f"AMC Expiry | {str(amc.customer)}",
            "start": amc.end_date.isoformat(),
            "backgroundColor": "#dc3545",
            "borderColor": "#dc3545",
            "extendedProps": {
                "type": "AMC Expiry",
                "contract": amc.contract_number,
                "customer": str(amc.customer),
                "branch": amc.branch.branch_name if amc.branch else "-",
                "date": amc.end_date.strftime("%d %b %Y"),
            }
        })

    return JsonResponse(events, safe=False)





from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import AMCServiceVisit
from .forms import AMCServiceVisitForm


@login_required
def edit_amc_visit(request, visit_id):

    visit = get_object_or_404(AMCServiceVisit, id=visit_id)

    # ✅ CHECK FROM SCHEDULE MODEL
    schedule = AMCServiceSchedule.objects.filter(
        amc=visit.amc,
        service_date=visit.service_date
    ).first()

    if schedule and schedule.is_completed:
        messages.error(
            request,
            "This visit is already completed and cannot be edited."
        )
        return redirect("amc:detail", visit.amc.id)

    if request.method == "POST":

        form = AMCServiceVisitForm(request.POST, instance=visit)

        if form.is_valid():

            old_service = visit.crm_service
            was_allocated = visit.allocation_status == "ALLOCATED"

            updated_visit = form.save(commit=False)

            # 🔥 CLEAN OLD CRM DATA IF ALREADY ALLOCATED
            if was_allocated and old_service:

                TechWorkList.objects.filter(
                    service=old_service
                ).delete()

                WorkAllocation.objects.filter(
                    service=old_service
                ).delete()

                updated_visit.crm_service = None
                updated_visit.crm_service_created_at = None
                updated_visit.allocation_status = "PENDING"
                updated_visit.allocation_cancelled_reason = "Visit rescheduled"
                updated_visit.rescheduled_from = visit.service_date

            updated_visit.save()

            # ✅ SAVE MANY TO MANY
            form.save_m2m()

            messages.success(
                request,
                "Visit updated successfully."
            )

            return redirect("amc:detail", visit.amc.id)

    else:
        form = AMCServiceVisitForm(instance=visit)

    return render(request, "amc/edit_visit.html", {
        "form": form,
        "visit": visit,
        "amc": visit.amc,
    })




from .forms import AMCDefaultAssignmentForm


from .utils import distance_km

@login_required
def assign_amc_technicians(request, amc_id):

    amc = get_object_or_404(AMCContract, id=amc_id)

    if request.method == "POST":

        form = AMCDefaultAssignmentForm(request.POST, instance=amc)

        if form.is_valid():

            amc = form.save(commit=False)
            amc.save()

            tech_ids = request.POST.getlist("technicians")
            selected_techs = TechnicianProfile.objects.filter(id__in=tech_ids)

            amc.technicians.set(selected_techs)

            service_lat = amc.service.latitude
            service_lon = amc.service.longitude

            for visit in amc.visits.all():

                assigned = False

                # find existing visits with same day + month
                existing_visits = AMCServiceVisit.objects.filter(
                    service_date__day=visit.service_date.day,
                    service_date__month=visit.service_date.month
                ).exclude(amc=amc)

                for old_visit in existing_visits:

                    old_service = old_visit.amc.service

                    if not old_service.latitude or not old_service.longitude:
                        continue

                    dist = distance_km(
                        service_lat,
                        service_lon,
                        old_service.latitude,
                        old_service.longitude
                    )

                    if dist <= 10 and old_visit.technicians.exists():

                        visit.technicians.set(old_visit.technicians.all())
                        assigned = True
                        break

                if not assigned:
                    visit.technicians.set(selected_techs)

            messages.success(request, "Technicians assigned successfully.")
            return redirect("amc:detail", amc.id)

    else:

        form = AMCDefaultAssignmentForm(instance=amc)

    return render(request, "amc/assign_technicians.html", {
        "amc": amc,
        "form": form,
        "technicians": TechnicianProfile.objects.all(),
    })



@login_required
def amc_assign_defaults(request, amc_id):
    amc = get_object_or_404(AMCContract, id=amc_id)

    if request.method == "POST":
        form = AMCDefaultAssignmentForm(request.POST, instance=amc)
        if form.is_valid():
            amc = form.save(commit=False)
            amc.save()

            # ✅ MANUALLY HANDLE TECHNICIANS
            tech_ids = request.POST.getlist("technicians")
            amc.technicians.set(tech_ids)

            # 🔁 Sync technicians to ALL future visits (not allocated)
            for visit in amc.visits.filter(crm_service__isnull=True):
                visit.technicians.set(amc.technicians.all())

            messages.success(
                request,
                "Default technicians & work details updated successfully."
            )
            return redirect("amc:detail", amc.id)

    else:
        form = AMCDefaultAssignmentForm(instance=amc)

    return render(request, "amc/assign_defaults.html", {
        "amc": amc,
        "form": form
    })





from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from crmapp.models import customer_details
from amc.models import AMCContract

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from crmapp.models import customer_details
from .models import AMCContract


@login_required
def find_customer_by_phone(request):
    phone = request.GET.get("phone")

    if not phone:
        return JsonResponse({"error": "Phone required"}, status=400)

    customer = customer_details.objects.filter(
        primarycontact=phone
    ).first()

    if not customer:
        return JsonResponse({"found": False})

    # 🔹 AMC contracts
    amcs = AMCContract.objects.filter(
        customer=customer
    ).select_related("service").order_by("-start_date")

    amc_list = []

    for amc in amcs:
        # ✅ SAFE SERVICE ACCESS
        service_name = ""

        try:
            if amc.service:
                service_name = amc.service.service_subject or f"Service #{amc.service.id}"
        except Exception:
            service_name = "Service Deleted"

        amc_list.append({
            "contract_number": amc.contract_number,
            "service": service_name,
            "start_date": amc.start_date.strftime("%d-%m-%Y") if amc.start_date else "",
            "end_date": amc.end_date.strftime("%d-%m-%Y") if amc.end_date else "",
            "amc_type": amc.amc_type,
            "status": amc.status
        })

    return JsonResponse({
        "found": True,
        "customer_id": customer.id,
        "customer_name": customer.fullname,
        "amcs": amc_list
    })





from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from amc.models import AMCContract


@login_required
def get_amc_details(request):

    contract = request.GET.get("contract")

    try:
        amc = AMCContract.objects.select_related(
            "customer",
            "service",
            "branch"
        ).get(contract_number=contract)

        data = {
            "contract": amc.contract_number,
            "customer": amc.customer.fullname,
            "service": amc.service.service_subject,
            "branch": str(amc.branch) if amc.branch else "",
            "start_date": amc.start_date.strftime("%d-%m-%Y"),
            "end_date": amc.end_date.strftime("%d-%m-%Y"),
            "frequency": amc.frequency,
            "total_amount": float(amc.total_amount),
            "per_visit_amount": float(amc.per_visit_amount),
            "amc_type": amc.amc_type,
            "status": amc.status,
        }

        products = []

        if hasattr(amc.service, "service_products"):
            for p in amc.service.service_products.all():
                products.append({
                    "name": p.product.product_name,
                    "price": float(p.price),
                    "qty": p.quantity,
                    "total": float(p.price * p.quantity)
                })

        data["products"] = products

        return JsonResponse(data)

    except AMCContract.DoesNotExist:
        return JsonResponse({"error": "AMC not found"}, status=404)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
    


from django.core.paginator import Paginator
from datetime import date

@login_required
def amc_list(request):
    amc_qs = AMCContract.objects.all().order_by("-created_at")

    paginator = Paginator(amc_qs, 10)
    page_number = request.GET.get("page")
    contracts = paginator.get_page(page_number)

    return render(request, "amc/list.html", {
        "contracts": contracts,
        "today": date.today(),
    })


