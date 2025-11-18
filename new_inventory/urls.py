from django.urls import path
from .views import *
urlpatterns = [ 
  path('vendor_add/', vendor_add, name="vendor_add"),
  path('vendor_list/', vendor_list, name="vendor_list"),
  path('vendor_edit/<int:id>/', vendor_edit, name='vendor_edit'),
  path('vendor_delete/<int:id>/', vendor_delete, name="vendor_delete"),
]