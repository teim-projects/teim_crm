from django.urls import path
from . import views

app_name = "amc"

urlpatterns = [

    # -----------------------
    # AMC CRUD
    # -----------------------
    path("", views.amc_list, name="list"),
    path("create/", views.amc_create, name="create"),
    path("<int:pk>/", views.amc_detail, name="detail"),
    path("<int:pk>/edit/", views.amc_edit, name="edit"),
    path("<int:pk>/delete/", views.amc_delete, name="delete"),

    # -----------------------
    # AJAX
    # -----------------------
    path("load-services/", views.load_services, name="load_services"),
    path("load-service-details/", views.load_service_details, name="load_service_details"),

    # -----------------------
    # VISITS
    # -----------------------
    path(
        "visit/<int:visit_id>/edit/",
        views.edit_amc_visit,
        name="edit_amc_visit"
    ),

    path(
        "find-customer-by-phone/",
        views.find_customer_by_phone,
        name="find_customer_by_phone"
    ),

    path(
        "get-amc-details/",
        views.get_amc_details,
        name="get_amc_details"
    ),


    # -----------------------
    # DASHBOARD & CALENDAR
    # -----------------------
    path("dashboard/", views.amc_dashboard, name="dashboard"),
    path("calendar/events/", views.amc_calendar_events, name="calendar_events"),

    # -----------------------
    # RENEWALS
    # -----------------------
    path(
        "renewal-requests/",
        views.renewal_requests,
        name="renewal_requests"
    ),

    # -----------------------
    # DEFAULT TECHNICIANS / AMC SETTINGS
    # -----------------------
    path(
        "amc/<int:amc_id>/assign-technicians/",
        views.assign_amc_technicians,
        name="assign_amc_technicians"
    ),

    path(
        "amc/<int:amc_id>/assign-defaults/",
        views.amc_assign_defaults,
        name="assign_defaults"
    ),
    

]