from django.urls import path
from .views import *

urlpatterns = [ 

    # ---------------- Destination Loader ----------------
    path("ajax/load-destinations/", load_destinations, name="load_destinations"),

    # ---------- batch loadr --------
    path("ajax/load-batches/", load_batches, name="load_batches"),
    # -------- Product details (description + unit) --------
    path(
        "ajax/product-details/<int:product_id>/",
        get_product_details,
        name="get_product_details"
    ),

    # ---------------- Service Stock Return ----------------
    path(
        "service/<int:service_id>/stock-return/",
        service_stock_return,
        name="service_stock_return",
    ),

    # ---------------- Vendor ----------------
    path('vendor_add/', vendor_add, name="vendor_add"),
    path('vendor_list/', vendor_list, name="vendor_list"),
    path('vendor_edit/<int:id>/', vendor_edit, name='vendor_edit'),
    path('vendor_delete/<int:id>/', vendor_delete, name="vendor_delete"),

    # ---------------- HO Staff ----------------
    path('add_ho_staff/', add_ho_staff, name='add_ho_staff'),
    path('ho_list/', ho_list, name="ho_list"),
    path('ho_edit/<int:pk>/', ho_edit, name="ho_edit"),
    path('ho_delete/<int:pk>/', ho_delete, name="ho_delete"),

    # ---------------- Sites ----------------
    path('add_site/', add_site, name="add_site"),
    path('site_list/', site_list, name="site_list"),
    path('site_edit/<int:id>/', site_edit, name="site_edit"),
    path('site_delete/<int:id>/', site_delete, name="site_delete"),

    # ---------------- Purchase Orders ----------------
    path("po_add/", purchase_order_create, name="purchase_order_create"),
    path("po_list/", purchase_order_list, name="purchase_order_list"),
    path("po_edit/<int:id>/", purchase_order_edit, name="purchase_order_edit"),
    path("po_delete/<int:id>/", purchase_order_delete, name="purchase_order_delete"),

    # ---------------- Purchase Order PDF ----------------
    path("po_pdf/<int:id>/", purchase_order_pdf, name="purchase_order_pdf"),

    # ---------------- GRN (Goods Receive Note) ----------------
    path("grn/create/<int:po_id>/", grn_create, name="grn_create"),
    path("grn/list/", grn_list, name="grn_list"),  
    path("grn/<int:grn_id>/", grn_detail, name="grn_detail"),
    path("grn/<int:pk>/edit/", grn_edit, name="grn_edit"),

    # Optional placeholder (when you create GRN list page)
    path('stock/products/', products_stock_list_view, name='products_stock_list'),
    path("products-stock/export/",export_products_stock_excel, name="export_products_stock_excel"),


    # -------MTN----
    path("mtn/fetch-qty/", fetch_mtn_available_qty, name="fetch_mtn_available_qty"),
    path("mtn/", mtn_list_view, name="mtn_list_view"),
    path('mtn/create/',create_mtn,name="mtn_create"),
    path("mtn/<int:pk>/", mtn_detail_view, name="mtn_detail_view"),
    path("mtn/<int:pk>/edit/", mtn_edit_view, name="mtn_edit_view"),

    # -----------Material Request ---------------
    path('mreq/create/', create_material_request, name="create_material_request"),
    path('mreq/list/', material_request_list, name="material_request_list"),
    path("mreq/<int:pk>/", material_request_detail,name="material_request_detail"),
    path("mreq/<int:pk>/approve/", approve_material_request, name="material_request_approve"),
    path("mreq/<int:pk>/reject/", reject_material_request, name="material_request_reject"), 



    path("notification/<int:pk>/", notification_read, name="notification_read"),
 



    path(
        "delivery-challan/create/<int:mtn_id>/",
        create_dc_from_mtn,
        name="create_dc_from_mtn"
    ),

    path(
        "delivery-challan/<int:pk>/",
        dc_detail_view,
        name="dc_detail_view"
    ),

    path(
        "delivery-challan/",
        dc_list_view,
        name="dc_list_view"
    ),

        path(
            "delivery-challan/edit/<int:pk>/",
            dc_edit_view,
            name="dc_edit"
        ),

     path("delivery-challan/<int:pk>/pdf/", dc_pdf_view, name="dc_pdf"),
    path("get-required-items/<int:product_id>/", get_required_items, name="get_required_items"),
    





]
