from django.urls import path
from .views import *

urlpatterns = [ 

    # ---------------- Destination Loader ----------------
    path("ajax/load-destinations/", load_destinations, name="load_destinations"),

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
    path("grn/<int:grn_id>/", grn_detail, name="grn_detail"),

    # Optional placeholder (when you create GRN list page)
    path("grn/list/", grn_list, name="grn_list"),  
    path('stock/products/', products_stock_list_view, name='products_stock_list'),
    # path('stock/product/<int:product_id>/', product_stock_view, name='product_stock_view'),
]
