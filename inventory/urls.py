from django.urls import path 
from .views import *
urlpatterns = [
    path('add-vendor/', addVendor, name='add_vendor'),
    path('vendor-list/', vendorList, name='vendor_list'),
]
