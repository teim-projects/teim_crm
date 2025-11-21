from django.urls import path
from .views import *
urlpatterns = [ 
  # ----- destination api url -----
  path("ajax/load-destinations/", load_destinations, name="load_destinations"),

  # --- Vendor urls ---
  path('vendor_add/', vendor_add, name="vendor_add"),
  path('vendor_list/', vendor_list, name="vendor_list"),
  path('vendor_edit/<int:id>/', vendor_edit, name='vendor_edit'),
  path('vendor_delete/<int:id>/', vendor_delete, name="vendor_delete"),

  # --- HO staff ---
  path('add_ho_staff/', add_ho_staff, name='add_ho_staff'),
  path('ho_list/', ho_list, name="ho_list"),
  path('ho_edit/<int:pk>/', ho_edit, name="ho_edit"),
  path('ho_delete/<int:pk>/',ho_delete, name="ho_delete"),

  # --- Site urls ------
  path('add_site/', add_site, name="add_site"),
  path('site_list/', site_list, name="site_list"),
  path('site_edit/<int:id>/', site_edit, name="site_edit"),
  path('site_delete/<int:id>/', site_delete, name="site_delete"),


  # --- PO -----
  path("po_add/", purchase_order_create, name="purchase_order_create"),
  path("po_list/", purchase_order_list, name="purchase_order_list"),
]