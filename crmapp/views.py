from decimal import Decimal
from django.shortcuts import render , redirect , HttpResponse , get_object_or_404
from httpcore import request
from .forms import InventoryServiceForm, InventoryAddForm ,  AddProductForm, UpdateProductForm
from django.utils import timezone
from crmapp.models import customer_details, service_management ,TaxInvoice, quotation ,invoice , lead_management , Product , Inventory_summary , Inventory_add  
from django .db.models import Q
import random
from django.http import JsonResponse
from django.http import HttpResponse
from django import contrib
from django.contrib.auth.models import User
from django.contrib.auth import authenticate,login,logout , admin
from django.db.models import Sum, Count
from crmapp.models import lead_management
from crmapp.models import firstfollowup
from crmapp.models import secondfollowup
from crmapp.models import thirdfollowup
from crmapp.models import finalfollowup
import csv
import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from django.shortcuts import render
from crmapp.models import lead_management

from django.shortcuts import render
from django.http import JsonResponse
from schedule_meetings.models import Meeting

import openpyxl
from .forms import LeadImportForm
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from .models import TechnicianProfile
from datetime import datetime
import json
from django.utils.dateparse import parse_date
from django.db.models import Count


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



def landing_page(request):
    return render(request , 'landing_page.html')


import json
from datetime import datetime
from django.db.models import Count, Sum, Q
from django.shortcuts import render

def index(request):
    # Fetch data for Service Management
    service_data = service_management.objects.values('selected_services').annotate(total_charges=Sum('total_charges'))

    # Fetch data for Quotations
    quotation_data = quotation.objects.values('quotation_date').annotate(total_amount=Sum('total_amount'))

    # Fetch data for Invoices
    invoice_data = invoice.objects.values('company_name').annotate(total_amount=Sum('total_amount'))

    # Fetch data for Lead Management
    lead_data1 = lead_management.objects.values('typeoflead').annotate(count=Count('id'))

    # Lead type chart data (filtered by enquirydate range)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    if start_date and end_date:
        filtered_leads = lead_management.objects.filter(enquirydate__range=[start_date, end_date])
    else:
        filtered_leads = lead_management.objects.all()

    lead_data = {
        "labels": ["Hot", "Warm", "Cold", "NotInterested", "LossOfOrder"],
        "datasets": [{
            "data": [
                filtered_leads.filter(typeoflead='Hot').count(),
                filtered_leads.filter(typeoflead='Warm').count(),
                filtered_leads.filter(typeoflead='Cold').count(),
                filtered_leads.filter(typeoflead='NotInterested').count(),
                filtered_leads.filter(typeoflead='LossofOrder').count()
            ],
            "backgroundColor": ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
        }]
    }
    lead_data_json = json.dumps(lead_data)

    # Follow-up remark chart data (from main_followup model)
    start_date_followup = request.GET.get('start_date_followup')
    end_date_followup = request.GET.get('end_date_followup')

    # Filter main_followup records by enquirydate if date range is provided
    from crmapp.models import main_followup  # Adjust import according to your app structure

    followup_queryset = main_followup.objects.all()
    if start_date_followup and end_date_followup:
        try:
            start_dt_followup = datetime.strptime(start_date_followup, "%Y-%m-%d")
            end_dt_followup = datetime.strptime(end_date_followup, "%Y-%m-%d")
            # Assuming main_followup has a date field like enquirydate or followup_date to filter by
            followup_queryset = followup_queryset.filter(enquirydate__range=[start_dt_followup, end_dt_followup])
        except ValueError:
            pass  # Ignore if date parsing fails

    # Count by followup_remark choices
    followup_counts = followup_queryset.values('followup_remark').annotate(count=Count('id'))
    # Prepare labels and counts based on your choices order
    followup_labels = [
        'Call not received',
        'Give next Follow up date',
        'Call Out of Coverage Area',
    ]
    # Create data list aligned with labels order
    followup_data_list = []
    for label in followup_labels:
        entry = next((item for item in followup_counts if item['followup_remark'] == label), None)
        followup_data_list.append(entry['count'] if entry else 0)

    # Bar chart data for products by category
    pest_control_count = Product.objects.filter(category='Pest Control').count()
    fumigation_count = Product.objects.filter(category='Fumigation').count()
    product_sell_count = Product.objects.filter(category='Product Sell').count()

    bar_chart_data = {
        "labels": ['Pest Control', 'Fumigation', 'Product Sell'],
        "datasets": [{
            "label": "Number of Products per Category",
            "data": [pest_control_count, fumigation_count, product_sell_count],
            "backgroundColor": ['#FF6384', '#36A2EB', '#FFCE56'],
        }]
    }

    # Contract Type Distribution chart filtering
    start_date_service = request.GET.get('start_date_service')
    end_date_service = request.GET.get('end_date_service')

    if start_date_service and end_date_service:
        start_date_service_obj = datetime.strptime(start_date_service, "%Y-%m-%d")
        end_date_service_obj = datetime.strptime(end_date_service, "%Y-%m-%d")
        service_data = service_management.objects.filter(
            Q(service_date__gte=start_date_service_obj) & Q(service_date__lte=end_date_service_obj)
        ).values("contract_type").annotate(count=Count("id")).order_by("contract_type")
    else:
        service_data = service_management.objects.values("contract_type").annotate(count=Count("id")).order_by("contract_type")

    labellist = [entry["contract_type"] for entry in service_data]
    countlist = [entry["count"] for entry in service_data]

    # Quotation and Invoice counts filtered by date and type
    start_date_qo = request.GET.get('start_date_qo')
    end_date_qo = request.GET.get('end_date_qo')
    filter_type = request.GET.get('filter_type')

    quotations_count = 0
    orders_count = 0

    if start_date_qo and end_date_qo:
        start_date_obj = datetime.strptime(start_date_qo, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date_qo, "%Y-%m-%d")
        if filter_type == 'quotation':
            quotations_count = quotation.objects.filter(
                Q(quotation_date__gte=start_date_obj) & Q(quotation_date__lte=end_date_obj)
            ).count()
            orders_count = invoice.objects.count()
        elif filter_type == 'invoice':
            orders_count = invoice.objects.filter(
                Q(date__gte=start_date_obj) & Q(date__lte=end_date_obj)
            ).count()
            quotations_count = quotation.objects.count()
    else:
        quotations_count = quotation.objects.count()
        orders_count = invoice.objects.count()

    context = {
        'lead_data': lead_data_json,
        'service_data': service_data,
        'quotation_data': quotation_data,
        'invoice_data': invoice_data,
        'labellist': json.dumps(labellist),
        'countlist': json.dumps(countlist),
        "quotationlist": json.dumps(["Quotations", "Orders"]),
        "order": json.dumps([quotations_count, orders_count]),
        'bar_chart_data': json.dumps(bar_chart_data),

        # Follow-up chart context
        'follow_up_labels': json.dumps(followup_labels),
        'follow_up_data': json.dumps(followup_data_list),
    }

    return render(request, 'index.html', context)

   

import random

def generate_customerid(fullname):
    names = fullname.strip().split()

    # Extract first and last name safely
    firstname = names[0] if names else ''
    lastname = names[-1] if len(names) > 1 else ''

    # Get first 3 letters (or less if name is short)
    first_part = firstname[:3].upper().ljust(3, 'X')
    last_part = lastname[:3].upper().ljust(3, 'X')

    # Generate 4-digit random number
    random_number = str(random.randint(1000, 9999))

    return first_part + last_part + random_number



from django.http import JsonResponse
from .models import customer_details
from django.db.models import Count, Max, Q


def get_customer_name(request):
    customer_id = request.GET.get('customer_id', None)
    if customer_id:
        try:
            customer = customer_details.objects.get(customerid=customer_id)
            customer_name = f"{customer.firstname} {customer.lastname}"
            return JsonResponse({'customer_name': customer_name})
        except customer_details.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)



from django.conf import settings
def signup(request):
    if request.method == "GET":
        return render(request, 'signup.html')
    else:
        uname = request.POST['uname']
        uemail = request.POST['uemail']
        upass = request.POST['upass']
        cpass = request.POST['cpass']
        security_key = request.POST.get('security_key', '')  # Retrieve the security key from the form

        # Check if fields are empty
        if uname == "" or upass == "" or cpass == "" or security_key == "":
            context = {'msg1': 'Field can not be empty'}
            return render(request, "signup.html", context)

        # Check if passwords match
        elif upass != cpass:
            context = {'msg2': 'Password and Confirm Password should be same'}
            return render(request, "signup.html", context)
        
        # Check if the security key is correct
        elif security_key != settings.SECURITY_KEY:
            context = {'msg2': 'Invalid security key'}
            return render(request, "signup.html", context)
        
        else:
            # Create the user
            u = User.objects.create(username=uname, email=uemail)
            u.set_password(upass)
            u.save()
            context = {'msg3': 'User Registered Successfully'}
            return render(request, "signup.html", context)



from django.db.models import Count, Max, Q
from django.db.models.functions import Lower

def user_login(request):
    if request.method == "GET":
        return render(request, 'login.html')
    
    else:
        uname = request.POST.get('uname')  # Use .get() to avoid MultiValueDictKeyError
        upass = request.POST.get('upass')

        u = authenticate(username=uname, password=upass)

        if u is not None:
            login(request, u)


           
            start_date = request.GET.get('start_date')
            end_date = request.GET.get('end_date')

            latest_followups_qs = main_followup.objects.values('lead').annotate(
                latest_id=Max('id')
            ).values_list('latest_id', flat=True)

            if start_date and end_date:
                filtered_leads = main_followup.objects.filter(
                    id__in=latest_followups_qs,
                    lead__enquirydate__range=[start_date, end_date]
                )
            else:
                filtered_leads = main_followup.objects.filter(id__in=latest_followups_qs)

            # Prepare lead type chart data
            lead_data = {
            "labels": ["Hot", "Warm", "Cold", "NotInterested", "LossOfOrder"],
            "datasets": [{
            "data": [
            filtered_leads.filter(typeoflead='Hot').count(),
            filtered_leads.filter(typeoflead='Warm').count(),
            filtered_leads.filter(typeoflead='Cold').count(),
            filtered_leads.filter(typeoflead='NotInterested').count(),
            filtered_leads.filter(typeoflead='LossofOrder').count()
             ],
                "backgroundColor": ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF'],
            }]
            }


            # Serialize the data to JSON
            lead_data_json = json.dumps(lead_data)

            # Retrieve the start and end dates from query parameters
            start_date_followup = request.GET.get('start_date_followup')
            end_date_followup = request.GET.get('end_date_followup')

            # Default to today's date if no date range is provided
            if start_date_followup:
                start_date_followup = datetime.strptime(start_date_followup, "%Y-%m-%d")
            if end_date_followup:
                end_date_followup = datetime.strptime(end_date_followup, "%Y-%m-%d")

            # Define the stages
            stages = {
                1: "No Follow-Up Done",
                2: "First Follow-Up Done",
                3: "Second Follow-Up Done",
                4: "Third Follow-Up Done",
                5: "Final Follow-Up Done"
            }

            # Filter the lead_management table by the date range if provided
            if start_date_followup and end_date_followup:
                stage_counts = lead_management.objects.filter(enquirydate__range=[start_date_followup, end_date_followup]) \
                    .values('stage') \
                    .annotate(count=Count('id')) \
                    .order_by('stage')
            else:
                # If no date range, fetch all data
                stage_counts = lead_management.objects.values('stage') \
                    .annotate(count=Count('id')) \
                    .order_by('stage')

            # Prepare the labels and data for the chart


            pest_control_count = Product.objects.filter(category='Pest Control').count()
            fumigation_count = Product.objects.filter(category='Fumigation').count()
            product_sell_count = Product.objects.filter(category='Product Sell').count()

            # Bar chart data
            bar_chart_data = {
                "labels": ['Pest Control', 'Fumigation', 'Product Sell'],
                "datasets": [{
                    "label": "Number of Products per Category",
                    "data": [pest_control_count, fumigation_count, product_sell_count],
                    "backgroundColor": ['#FF6384', '#36A2EB', '#FFCE56'],
                }]
            }

            print('testtttttttttttttttttttt')



            # Extract service-specific date filters
            start_date_service = request.GET.get('start_date_service')
            end_date_service = request.GET.get('end_date_service')

            # Filter service management data by service_date range if present
            if start_date_service and end_date_service:
                start_date_service_obj = datetime.strptime(start_date_service, "%Y-%m-%d")
                end_date_service_obj = datetime.strptime(end_date_service, "%Y-%m-%d")

                # Apply date filter on service_date field for contract type distribution
                service_data = service_management.objects.filter(
                    Q(service_date__gte=start_date_service_obj) & Q(service_date__lte=end_date_service_obj)
                ).values("contract_type").annotate(count=Count("id")).order_by("contract_type")
            else:
                # Default data if no service date filter is applied
                service_data = service_management.objects.values("contract_type").annotate(count=Count("id")).order_by("contract_type")

            # Prepare data for the Contract Type Distribution chart
            labellist = [entry["contract_type"] for entry in service_data]
            countlist = [entry["count"] for entry in service_data]

            # Extract query parameters
            start_date_qo = request.GET.get('start_date_qo')
            end_date_qo = request.GET.get('end_date_qo')
            filter_type = request.GET.get('filter_type')

            # Initialize counts
            quotations_count = 0
            orders_count = 0

            # Apply date filters if present
            if start_date_qo and end_date_qo:
                # Parse dates
                start_date_obj = datetime.strptime(start_date_qo, "%Y-%m-%d")
                end_date_obj = datetime.strptime(end_date_qo, "%Y-%m-%d")

                if filter_type == 'quotation':
                    # Filter quotations by date range
                    quotations_count = quotation.objects.filter(
                        Q(quotation_date__gte=start_date_obj) & Q(quotation_date__lte=end_date_obj)
                    ).count()
                    orders_count = invoice.objects.count()  # Unfiltered
                elif filter_type == 'invoice':
                    # Filter invoices by date range
                    orders_count = invoice.objects.filter(
                        Q(date__gte=start_date_obj) & Q(date__lte=end_date_obj)
                    ).count()
                    quotations_count = quotation.objects.count()  # Unfiltered
            else:
                # Default counts without filters
                quotations_count = quotation.objects.count()
                orders_count = invoice.objects.count()
            
            
            # Prepare context
            context = {
                # 'total_leads': leads.count(),
                # 'hot_leads': hot_leads,
                # 'warm_leads': warm_leads,
                # 'cold_leads': cold_leads,
                # 'not_interested': not_interested,
                # 'loss_of_order': loss_of_order,
                'lead_data': lead_data_json,
                'service_data': service_data,
                # 'quotation_data': quotation_data,
                # 'invoice_data': invoice_data,
                # 'lead_data1': lead_data1,
                'labellist': json.dumps(labellist),  # Serialize labels
                'countlist': json.dumps(countlist),  # Serialize counts
                "quotationlist": json.dumps(["Quotations", "Orders"]),
                "order": json.dumps([quotations_count, orders_count]),
                'lead_data': json.dumps(lead_data),
                'bar_chart_data': json.dumps(bar_chart_data),
                
            }
            print("chartctfgvbhjnbgtfvrdcew:::::::::::::::::::")


            return render(request, 'index.html', context)


            # return render(request, "index.html")
        

        else:
            context = {'msg1': 'Wrong Username Or Password'}
            return render(request, "login.html", context)
        

    
def user_logout(request):

    logout(request)

    return redirect("/")









from django.shortcuts import render, redirect, get_object_or_404
from .models import SalesPerson
from django.utils.dateparse import parse_date

# Add Sales Person
def add_sales_person(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name')
        date_of_joining = parse_date(request.POST.get('date_of_joining'))
        mobile_no = request.POST.get('mobile_no')
        email = request.POST.get('email')
        date_of_birth = parse_date(request.POST.get('date_of_birth'))

        SalesPerson.objects.create(
            full_name=full_name,
            date_of_joining=date_of_joining,
            mobile_no=mobile_no,
            email=email,
            date_of_birth=date_of_birth
        )
        return redirect('sales_person_list')

    return render(request, 'add_sales_person.html')


# List Sales Persons
def sales_person_list(request):
    sales_persons = SalesPerson.objects.all()
    return render(request, 'sales_person_list.html', {'sales_persons': sales_persons})


# Edit Sales Person
def edit_sales_person(request, pk):
    person = get_object_or_404(SalesPerson, pk=pk)

    if request.method == 'POST':
        person.full_name = request.POST.get('full_name')
        person.date_of_joining = parse_date(request.POST.get('date_of_joining'))
        person.mobile_no = request.POST.get('mobile_no')
        person.email = request.POST.get('email')
        person.date_of_birth = parse_date(request.POST.get('date_of_birth'))
        person.save()
        return redirect('sales_person_list')

    return render(request, 'edit_sales_person.html', {'person': person})


# Delete Sales Person
def delete_sales_person(request, pk):
    person = get_object_or_404(SalesPerson, pk=pk)

    if request.method == 'POST':
        person.delete()
        return redirect('sales_person_list')

    return render(request, 'delete_sales_person.html', {'person': person})







from django.http import JsonResponse
from .models import customer_details, lead_management

def customer_details_create(request):
    if request.method == 'GET':
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            primarycontact = request.GET.get('primarycontact')
            lead = lead_management.objects.filter(primarycontact=primarycontact).order_by('-enquirydate').first()
            if lead:
                data = {
                    'fullname': lead.customername or '',
                    'primaryemail': lead.customeremail or '',
                    'secondarycontact': lead.secondarycontact or '',
                    'contactperson': lead.contactedby or '',
                    'customersegment': lead.customersegment or '',
                    'shifttopartyaddress': lead.customeraddress or '',
                    'shifttopartycity': lead.city or '',
                    'soldtopartyaddress': lead.customeraddress or '',
                    'soldtopartycity': lead.city or '',
                }
                return JsonResponse({'status': 'exists', 'data': data})
            return JsonResponse({'status': 'not_found'})
        return render(request, 'customer_details.html')

    else:
        fullname = request.POST['fullname']
        primaryemail = request.POST['primaryemail']
        secondaryemail = request.POST['secondaryemail']
        primarycontact = request.POST['primarycontact']
        secondarycontact = request.POST['secondarycontact'] or None
        contactperson = request.POST['contactperson']
        customersegment = request.POST['customersegment']
        shifttopartyaddress = request.POST['shifttopartyaddress']
        shifttopartycity = request.POST['shifttopartycity']
        shifttopartystate = request.POST['shifttopartystate']
        shifttopartypostal = request.POST['shifttopartypostal']
        soldtopartyaddress = request.POST['soldtopartyaddress']
        soldtopartycity = request.POST['soldtopartycity']
        soldtopartystate = request.POST['soldtopartystate']
        soldtopartypostal = request.POST['soldtopartypostal']

        if not fullname or not primaryemail or not primarycontact:
            return render(request, "customer_details.html", {'msg1': 'Field cannot be empty'})

        customerid = generate_customerid(fullname)

        customer_details.objects.create(
            fullname=fullname,
            primaryemail=primaryemail,
            secondaryemail=secondaryemail,
            primarycontact=primarycontact,
            secondarycontact=secondarycontact,
            contactperson=contactperson,
            customersegment=customersegment,
            shifttopartyaddress=shifttopartyaddress,
            shifttopartycity=shifttopartycity,
            shifttopartystate=shifttopartystate,
            shifttopartypostal=shifttopartypostal,
            soldtopartyaddress=soldtopartyaddress,
            soldtopartycity=soldtopartycity,
            soldtopartystate=soldtopartystate,
            soldtopartypostal=soldtopartypostal,
            customerid=customerid
        )
        return redirect('/display_customer')


from django.shortcuts import render
from .models import Product

from django.shortcuts import render
from .models import Product
def product_list(request):
    category_filter = request.GET.get('category', 'all')
    if category_filter and category_filter != 'all':
        products = Product.objects.filter(category=category_filter)
    else:
        products = Product.objects.all()

    categories = Product.CATEGORY_CHOICES
    categories = [choice[0] for choice in categories]

    context = {
        'products': products,
        'categories': categories,
        'selected_category': category_filter,
    }
    return render(request, 'product_list.html', context)





def delete_product(request, product_id):
    product = get_object_or_404(Product, product_id=product_id)
    product.delete()
    return redirect('/products')


from django.shortcuts import render, redirect
from django.utils import timezone
from .models import service_management, customer_details


def service_management_create(request):
    customers = customer_details.objects.all()
    category_choices = Product.CATEGORY_CHOICES  # Pass category choices to the template
    print("category choice0", category_choices)
    products = Product.objects.all()  # Adjust filter as necessary
    print("product in all ", products)

    if request.method == 'POST':
        try:
            # Parse and validate form data
            customer_id = request.POST['customer_id']
            customer = customer_details.objects.get(id=customer_id)
            address=request.POST.get('address', 'Null')
            lead_date = request.POST.get('lead_date')
            service_date = request.POST.get('service_date')
            lead_date = datetime.strptime(lead_date, '%Y-%m-%d').date() if lead_date else None
            service_date = datetime.strptime(service_date, '%Y-%m-%d').date() if service_date else None
            
            # Extract and validate selected services
            selected_service_names = request.POST.get('selected_services_names', '').strip()
            if not selected_service_names:
                raise ValueError("No services selected. Please select at least one service.")

            selected_service_names_list = selected_service_names.split(',') if selected_service_names else []
            print(f"Selected Product Names: {selected_service_names_list}")

            # Validate price fields
            total_price = request.POST.get('total_price', '').strip()
            total_with_gst = request.POST.get('total_with_gst', '').strip()

            if not total_price or not total_price.replace('.', '', 1).isdigit():
                raise ValueError("Invalid total price. Please provide a valid number.")
            if total_with_gst and not total_with_gst.replace('.', '', 1).isdigit():
                raise ValueError("Invalid total price with GST. Please provide a valid number.")

            total_price = float(total_price)
            total_with_gst = float(total_with_gst) if total_with_gst else None

            # Determine if GST should be applied
            apply_gst = request.POST.get('apply_gst') == 'on'
            gst_number = request.POST.get('gst_number', '') if apply_gst else ''
            if apply_gst :
                gst_status = 'GST'
            else :
                total_with_gst = total_price   
                gst_status = 'NON-GST'    
            delivery_time = request.POST['delivery_time']

            # Create and save the service management instance
            instance = service_management(

                customer=customer,
                address = address,
                # gst_checkbox=apply_gst,  # Store whether GST is applied
                # gst_number=gst_number,  # Save GST number only if provided
                # gst_status = gst_status,
                total_price=total_price,
                total_price_with_gst=total_with_gst,
                contract_type=request.POST.get('contract_type', 'NOT SELECTED'),
                contract_status=request.POST.get('contract_status', 'NOT SELECTED'),
                property_type=request.POST.get('property_type'),
                warranty_period=request.POST.get('warranty_period'),
                state=request.POST.get('state', 'Null'),
                city=request.POST.get('city', 'Null'),
                pincode=request.POST.get('pincode', '000000'),
               
                gps_location=request.POST.get('gps_location'),
                frequency_count=request.POST.get('frequency_count', 'NOT SELECTED'),
                payment_terms=request.POST.get('payment_terms', '100% Advance payment OR Whatever mutually Decided'),
                sales_person_name=request.POST.get('sales_person_name'),
                sales_person_contact_no=request.POST.get('sales_person_contact_no'),
                delivery_time=delivery_time,
                lead_date=lead_date,
                service_date=service_date,
            )

            # Save the instance first before assigning many-to-many fields
            instance.save()
            print("Instance saved:", instance.customer)
            # technician = TechnicianProfile.objects.all()
            # Fetch and assign selected products
            products = Product.objects.filter(product_name__in=selected_service_names_list)
            if not products.exists():
                raise ValueError("Selected products not found in the database.")

            print("Selected products:", products)
            instance.selected_services.set(products)
            instance.save()


            return redirect('/display_service_management')  # Redirect after successful submission

        except Exception as e:
            # Handle any errors
            print(f"Error: {e}")
            return render(request, 'service_management.html', {
                'error': str(e),
                'category_choices': category_choices,
                'products': products,
                'customers' : customers,
            })

    return render(request, 'service_management.html', {'category_choices': category_choices, 'products': products,'customers' : customers})



from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime
from .models import quotation_management, customer_details, Product, QuotationTerm
from django.shortcuts import render, redirect
from django.http import JsonResponse
from datetime import datetime
from django.utils import timezone
from .models import Product, QuotationTerm, quotation_management, customer_details

from django.shortcuts import render
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime
from .models import quotation_management, QuotationTerm
from .models import Product
from .models import customer_details
from .models import Branch  # ✅ Import branch model
#eee

# New----------------
def quotation_management_create(request):
    category_choices = Product.CATEGORY_CHOICES
    products = Product.objects.all()
    terms = QuotationTerm.objects.all()
    branches = Branch.objects.all()

    if request.method == 'POST':
        try:
            # Core data
            customer_full_name = request.POST.get('customer_full_name')
            contact_no = request.POST.get('contact_no')
            secondary_contact_no = request.POST.get('secondary_contact_no')
            customer_email = request.POST.get('customer_email')
            secondary_email = request.POST.get('secondary_email')
            contact_by = request.POST.get('contact_by')
            contact_by_no = request.POST.get('contact_by_no')
            address = request.POST.get('address')
            city = request.POST.get('city')
            state = request.POST.get('state')
            gps_location = request.POST.get('gps_location')
            pincode = request.POST.get('pincode', '000000')
            subject = request.POST.get('subject')
            branch_id = request.POST.get('branch_id')
            product_details_json = request.POST.get('product_details_json')

            # Handle quotation date
            date_str = request.POST.get('quotation_date')
            if date_str:
                try:
                    quotation_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    quotation_date = timezone.now().date()
            else:
                quotation_date = timezone.now().date()

            selected_service_names_list = request.POST.get('selected_services_names', '').split(',')
            selected_service_names_list = list(set(name.strip() for name in selected_service_names_list if name.strip()))
            if not selected_service_names_list:
                raise ValueError("No services selected. Please select at least one service.")

            selected_services = Product.objects.filter(product_name__in=selected_service_names_list).distinct()
            if not selected_services.exists():
                raise ValueError("Selected services are invalid or not found.")

            # Prices and GST
            total_price = request.POST.get('total_price', '').strip()
            total_gst = request.POST.get('total_gst', '0').strip()
            total_price_with_gst = request.POST.get('total_with_gst', '').strip()
            
            # Validate prices
            try:
                total_price = float(total_price)
                total_gst = float(total_gst) if total_gst else 0
                total_price_with_gst = float(total_price_with_gst) if total_price_with_gst else total_price
    
    # Ensure total_with_gst is at least total_price
                if total_price_with_gst < total_price:
                    total_price_with_gst = total_price + total_gst
            except (ValueError, TypeError):
                raise ValueError("Invalid price values")

            enable_gst = request.POST.get('enable_gst') == 'on'
            gst_type = request.POST.get('gst_type', 'cgst_sgst')
            
            # Calculate CGST, SGST, IGST based on GST type
            if enable_gst:
                gst_status = 'GST'
                if gst_type == 'cgst_sgst':
                    cgst = total_gst / 2
                    sgst = total_gst / 2
                    igst = 0
                else:
                    cgst = 0
                    sgst = 0
                    igst = total_gst
                total_price_with_gst = total_price + total_gst    
            else:
                gst_status = 'NON-GST'
                cgst = 0
                sgst = 0
                igst = 0
                total_gst = 0

                total_price_with_gst = total_price

            # Create the quotation
            quotation = quotation_management.objects.create(
                customer_full_name=customer_full_name,
                contact_no=contact_no,
                secondary_contact_no=secondary_contact_no,
                customer_email=customer_email,
                secondary_email=secondary_email,
                contact_by = contact_by,
                contact_by_no = contact_by_no,
                address=address,
                city=city,
                state=state,
                gps_location=gps_location,
                pincode=pincode,
                subject=subject,
                quotation_date=quotation_date,
                apply_gst=enable_gst,
                gst_status=gst_status,
                total_charges=total_price,
                total_price=total_price,
                total_price_with_gst=total_price_with_gst,
                cgst=cgst,
                sgst=sgst,
                igst=igst,
                gst_total=total_gst,
                branch_id=branch_id if branch_id else None,
                product_details_json=json.loads(product_details_json) 
            )

            quotation.selected_services.set(selected_services)
            selected_term_ids = request.POST.getlist('terms_and_conditions')
            quotation.terms_and_conditions.set(selected_term_ids)

            return redirect('/display_quotation')

        except Exception as e:
            print(f"Error saving quotation: {e}")
            return render(request, 'quotation_create_new.html', {
                'error': str(e),
                'products': products,
                'category_choices': category_choices,
                'terms': terms,
                'branches': branches
            })

    return render(request, 'quotation_create_new.html', {
        'products': products,
        'category_choices': category_choices,
        'terms': terms,
        'branches': Branch.objects.all()  # Add this line
})
from django.http import JsonResponse
from .models import quotation_management




def get_quotation_details_by_no(request):
    quotation_no = request.GET.get('quotation_no')
    if not quotation_no:
        return JsonResponse({'error': 'Quotation number is required'}, status=400)

    try:
        quotation = quotation_management.objects.select_related('branch').get(quotation_no=quotation_no)
        branch = quotation.branch
        product = quotation.product_details_json
        cgst = quotation.cgst
        sgst = quotation.sgst
        igst = quotation.igst
        total = quotation.total_price_with_gst
        bank_accounts = BankAccounts.objects.all().values('id', 'bank_name', 'account_number', 'ifs_code', 'branch')
        # Fetch customer manually by customer_id string field
        customer_contact = quotation.contact_no
        customer = customer_details.objects.get(primarycontact=customer_contact)


        return JsonResponse({
            # Branch data
            'branch_name':branch.branch_name if branch else '',
            'branch_contact_1': branch.contact_1 if branch else '',
            'branch_email_1': branch.email_1 if branch else '',
            'branch_gst': branch.gst_number if branch else '',
            'branch_pan': branch.pan_number if branch else '',
            'branch_address': branch.full_address if branch else '',
            'state':branch.state if branch else '',
            'code':branch.code if branch else '',

            # Customer data
            'fullname': customer.fullname,
            'primarycontact': customer.primarycontact,
            'primaryemail': customer.primaryemail,
            'soldtopartyaddress': customer.soldtopartyaddress,
            'soldtopartycity': customer.soldtopartycity,
            'soldtopartystate': customer.soldtopartystate,
            'soldtopartypostal': customer.soldtopartypostal,
            'shifttopartyaddress': customer.shifttopartyaddress,
            'shifttopartycity': customer.shifttopartycity,
            'shifttopartystate': customer.shifttopartystate,
            'shifttopartypostal': customer.shifttopartypostal,
            
            # Product data
            'product':product,
            'cgst':cgst,
            'sgst':sgst,
            'igst':igst,
            'total':total,
            

            # Bank data
            'bank': list(bank_accounts),
            'state_map': state_map,
        })

    except quotation_management.DoesNotExist:
        return JsonResponse({'error': 'Quotation not found'}, status=404)
    except customer_details.DoesNotExist:
        return JsonResponse({'error': 'Customer not found for this quotation'}, status=404)
    
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import quotation_management

def generate_quotation_pdf_download(request, id):
    quotation = quotation_management.objects.get(id=id)
    template_path = 'pdf_template.html'
    context = {'quotation': quotation}
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="quotation_{quotation.id}.pdf"'
    template = get_template(template_path)
    html = template.render(context)

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response




from django.http import HttpResponse
from django.template.loader import get_template
from crmapp.custom_filters import price_in_words
from xhtml2pdf import pisa
import json
import os

def generate_quotation_pdf_view(request, id):
    quotation = quotation_management.objects.get(id=id)

    # Safely parse the product_details_json
    product_data = quotation.product_details_json
    if isinstance(product_data, str):
        try:
            product_data = json.loads(product_data)
        except json.JSONDecodeError:
            product_data = []

    # Add total for each product (price × quantity)
    for product in product_data:
        try:
            product['total'] = round(float(product['price']) * float(product['quantity']), 2)
        except (KeyError, ValueError, TypeError):
            product['total'] = 0.0

    # Inject updated data into quotation object for template access
    quotation.product_details_json = product_data
    amount_in_words = price_in_words(quotation.total_price_with_gst)
 
    # Render PDF
    
    template_path = 'pdf_template.html'  
    logo_path = request.build_absolute_uri(static('images/Logo.png'))
    fottor_path = request.build_absolute_uri(static('images/qutation_fottor_pdf.jpg'))
  
    
    context = {'quotation': quotation,
               'amount_in_words': amount_in_words,
               'logo_path': logo_path,
               'fottor_path':  fottor_path
                }
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="quotation.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF', status=500)
    return response


def get_products_by_category(request):
    categories = request.GET.get('categories', '')
    category_list = categories.split(',') if categories else []

    products = Product.objects.filter(category__in=category_list).values('product_id', 'product_name')
    product_list = [{'product_id': product['product_id'], 'product_name': product['product_name']} for product in products]

    return JsonResponse({'products': product_list})

from django.http import JsonResponse

def get_customer_fullname(request, customer_id):
    customer = customer_details.objects.get(id=customer_id)
    full_name = f"{customer.firstname} {customer.lastname}"
    return JsonResponse({'full_name': full_name})
  



from django.shortcuts import render, redirect, get_object_or_404
from .models import QuotationTerm, InvoiceTerm

# --- QUOTATION ---
def add_quotation_term(request):
    if request.method == 'POST':
        QuotationTerm.objects.create(description=request.POST.get('description'))
        return redirect('view_quotation_terms')
    return render(request, 'add_quotation_term.html')

def edit_quotation_term(request, id):
    term = get_object_or_404(QuotationTerm, id=id)
    if request.method == 'POST':
        term.description = request.POST.get('description')
        term.save()
        return redirect('view_quotation_terms')
    return render(request, 'edit_quotation_term.html', {'term': term})

def view_quotation_terms(request):
    terms = QuotationTerm.objects.all()
    return render(request, 'view_quotation_terms.html', {'terms': terms})

def delete_quotation_term(request, id):
    term = get_object_or_404(QuotationTerm, id=id)
    term.delete()
    return redirect('view_quotation_terms')


# --- INVOICE ---
def add_invoice_term(request):
    if request.method == 'POST':
        InvoiceTerm.objects.create(description=request.POST.get('description'))
        return redirect('view_invoice_terms')
    return render(request, 'add_invoice_term.html')

def edit_invoice_term(request, id):
    term = get_object_or_404(InvoiceTerm, id=id)
    if request.method == 'POST':
        term.description = request.POST.get('description')
        term.save()
        return redirect('view_invoice_terms')
    return render(request, 'edit_invoice_term.html', {'term': term})

def view_invoice_terms(request):
    terms = InvoiceTerm.objects.all()
    return render(request, 'view_invoice_terms.html', {'terms': terms})

def delete_invoice_term(request, id):
    term = get_object_or_404(InvoiceTerm, id=id)
    term.delete()
    return redirect('view_invoice_terms')



# def quotation_create(request):
#     customers = customer_details.objects.all()

#     if request.method == 'POST':
#         quantity = int(request.POST.get('quantity'))
#         price = float(request.POST.get('price'))

#         total_amount = quantity * price
#         discount = float(request.POST.get('discount'))
#         company_name = request.POST.get('company_name')
#         company_email = request.POST.get('company_email')
#         company_contact_no = request.POST.get('company_contact_no')
#         quotation_date = request.POST.get('quotation_date')
#         company_address = request.POST.get('company_address')
#         subject = request.POST.get('subject')
#         termsandcondition = request.POST.get('termsandcondition')
#         servicetype_q = request.POST.get('servicetype_q')
#         gst_checkbox = request.POST.get('gst_checkbox') == 'on'
#         customer_id = request.POST.get('customer_id')
#         customer = customer_details.objects.get(id=customer_id)

#         discounted_amount = total_amount - (total_amount * (discount / 100))
#         total_amount_with_gst = discounted_amount * 1.18 if gst_checkbox else discounted_amount

#         # Get latest version of quotation for the customer
#         latest_quotation = quotation.objects.filter(customer=customer, servicetype_q=servicetype_q).order_by('-version').first()

#         # Increment version for the new quotation
#         if latest_quotation:
#             new_version = latest_quotation.version + 1
#         else:
#             new_version = 1

#         # Create quotation object and save to database
#         quotation_obj = quotation(
#             total_amount=total_amount,
#             discount=discount,
#             company_name=company_name,
#             company_email=company_email,
#             company_contact_no=company_contact_no,
#             quotation_date=quotation_date,
#             company_address=company_address,
#             subject=subject,
#             quantity=quantity,
#             price=price,
#             termsandcondition=termsandcondition,
#             servicetype_q=servicetype_q,
#             gst_checkbox=gst_checkbox,
#             customer=customer,
#             total_amount_with_gst=total_amount_with_gst,
#             version = new_version,
#             status = 'active'
#         )

#         # Mark the previous version as inactive
#         if latest_quotation:
#             latest_quotation.status = 'inactive'
#             latest_quotation.save()

#         quotation_obj.save()
#         return redirect('/display_quotation')  

#     context = {
#         'customers': customers,
#     }
#     return render(request, 'quotation.html', context)


def quotation_history(request, customer_id):
    customer = customer_details.objects.get(id=customer_id)
    quotations = quotation.objects.filter(customer=customer).order_by('-version')  # Get all versions of quotations

    context = {
        'customer': customer,
        'quotations': quotations,
    }
    return render(request, 'quotation_history.html', context)



import random
from django.utils.timezone import now
import string

def generate_invoice_number():
    # Use "INV" as the first 3 characters
    alphanumeric_part = "INV"

    # Generate remaining 7 digits
    numeric_part = ''.join(random.choices(string.digits, k=7))

    # Combine both parts
    invoice_no = alphanumeric_part + numeric_part

    return invoice_no



def invoice_create(request):
    customers = customer_details.objects.all()  # Fetch all customers from the database

    if request.method == 'POST':
        modeofpayment = request.POST['modeofpayment']
        dispatchedthrough = request.POST['dispatchedthrough']
        termofdelivery = request.POST['termofdelivery']
        termsandcondition = request.POST['termsandcondition']
        company_name = request.POST['company_name']
        company_email = request.POST['company_email']
        company_contact_no = request.POST['company_contact_no']
        description_of_goods = request.POST['description_of_goods']
        hsn_sac_code = request.POST['hsn_sac_code']
        quantity = int(request.POST['quantity'])
        price = float(request.POST['price'])
        discount = float(request.POST['discount']) if request.POST['discount'] else None
        gst_checkbox = True if 'gst_checkbox' in request.POST else False
        pan_card_no = request.POST['pan_card_no']
        account_no = request.POST['account_no']
        branch = request.POST['branch']
        ifsc_code = request.POST['ifsc_code']
        delivery_date = request.POST['delivery_date']
        dispatched_date = request.POST['dispatched_date']
        designation = request.POST['designation']
        customer_id = request.POST['customer_id']
        customer = customer_details.objects.get(id=customer_id)
        invoice_no = generate_invoice_number()
        total_amount = quantity * price
        
        discounted_amount = total_amount - (total_amount * (discount / 100))
        total_amount_with_gst = discounted_amount * 1.18 if gst_checkbox else discounted_amount

        m = invoice.objects.create(
            modeofpayment=modeofpayment,
            dispatchedthrough=dispatchedthrough,
            termofdelivery=termofdelivery,
            termsandcondition=termsandcondition,
            company_name=company_name,
            company_email=company_email,
            company_contact_no=company_contact_no,
            description_of_goods=description_of_goods,
            hsn_sac_code=hsn_sac_code,
            quantity=quantity,
            price=price,
            discount=discount,
            gst_checkbox=gst_checkbox,
            pan_card_no=pan_card_no,
            account_no=account_no,
            branch=branch,
            ifsc_code=ifsc_code,
            delivery_date=delivery_date,
            dispatched_date=dispatched_date,
            designation=designation,
            customer=customer,
            total_amount_with_gst=total_amount_with_gst,
            total_amount=total_amount,
            invoice_no=invoice_no,

        )

        m.save()
        return redirect('/display_invoice') 
        
    context = {
        'customers': customers,
        }
    return render(request, 'invoice.html', context)

   
def firstfollowup_create(request,lead_id,next_stage):
    lead = get_object_or_404(lead_management, id=lead_id)
    lead.stage = next_stage
    lead.save()

    if request.method == 'POST':
        havedonepestcontrolearlier = request.POST['havedonepestcontrolearlier']
        agency = request.POST['agency']
        inspectiononsite = request.POST['inspectiononsite']
        levelofinspection = request.POST['levelofinspection']
        quotationgiven = request.POST['quotationgiven']
        quotationamount = float(request.POST['quotationamount'])
        mailsent = request.POST['mailsent']
        customermeeting = request.POST['customermeeting']
        firstremark = request.POST['firstremark']
        secondfollowupdate = request.POST['secondfollowupdate']

        m = firstfollowup.objects.create(
            havedonepestcontrolearlier=havedonepestcontrolearlier,
            agency=agency,
            inspectiononsite=inspectiononsite,
            levelofinspection=levelofinspection,
            quotationgiven=quotationgiven,
            quotationamount=quotationamount,
            mailsent=mailsent,
            customermeeting=customermeeting,
            firstremark=firstremark,
            secondfollowupdate=secondfollowupdate,
            lead=lead,
        )

        m.save()
        return redirect('/display_followup') 
        
    context = {
        'lead': lead,
    }
    return render(request, 'first_followup.html', context)

def secondfollowup_create(request,lead_id,next_stage):
    lead = get_object_or_404(lead_management, id=lead_id)
    lead.stage = next_stage
    lead.save()

    if request.method == 'POST':
        negotiationstage = request.POST['negotiationstage']
        mailsent2 = request.POST['mailsent2']
        secondremark = request.POST['secondremark']
        thirdfollowupdate = request.POST['thirdfollowupdate']

        m = secondfollowup.objects.create(
            negotiationstage=negotiationstage,
            mailsent2=mailsent2,
            secondremark=secondremark,
            thirdfollowupdate=thirdfollowupdate,
            lead=lead,
        )

        m.save()
        return redirect('/display_followup') 
        
    context = {
        'lead': lead,
        }
    return render(request, 'second_followup.html', context)

def thirdfollowup_create(request,lead_id,next_stage):
    lead = get_object_or_404(lead_management, id=lead_id)
    lead.stage = next_stage
    lead.save()

    if request.method == 'POST':
        thirdremark = request.POST['thirdremark']
        fourthfollowupdate = request.POST['fourthfollowupdate']

        m = thirdfollowup.objects.create(
            thirdremark=thirdremark,
            fourthfollowupdate=fourthfollowupdate,
            lead=lead,
        )

        m.save()
        return redirect('/display_followup') 
        
    context = {
        'lead': lead,
        }
    return render(request, 'third_followup.html', context)

def finalfollowup_create(request,lead_id,next_stage):
    lead = get_object_or_404(lead_management, id=lead_id)
    lead.stage = next_stage
    lead.save()
    
    if request.method == 'POST':
        fourthremark = request.POST['fourthremark']
        finalstatus = request.POST['finalstatus']
        contracttype = request.POST['contracttype']
        bookingamount = request.POST['bookingamount']

        m = finalfollowup.objects.create(
            fourthremark=fourthremark,
            finalstatus=finalstatus,
            contracttype=contracttype,
            bookingamount=bookingamount,
            lead=lead,
        )

        m.save()
        return redirect('/display_followup') 
        
    context = {
        'lead': lead,
        }
    return render(request, 'final_followup.html', context)

# def inventory_create(request):
#     if request.method=='GET':
#         return render(request ,'inventory.html')
    
    
#     else:
#         itemnumber=request.POST['itemnumber']
#         itemname=request.POST['itemname']
#         price=request.POST['price']
#         quantity=request.POST['quantity']
        
    
#         m=inventory.objects.create(itemnumber=itemnumber, itemname=itemname , price=price ,quantity=quantity )

#         m.save()
#         return redirect( '/index')
    


from django.http import JsonResponse
from .models import lead_management

def check_phone_number(request):
    phone = request.GET.get('primarycontact', None)
    exists = lead_management.objects.filter(primarycontact=phone).exists()
    return JsonResponse({'exists': exists})



from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import lead_management
from datetime import datetime
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import lead_management
from datetime import datetime

from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import lead_management
from datetime import datetime

# change


def lead_management_create(request):
    salespersons = SalesPerson.objects.all()

    if request.method == 'GET':
        # Handle AJAX GET for mobile number lookup
        if request.headers.get('x-requested-with') == 'XMLHttpRequest' and 'primarycontact' in request.GET:
            primarycontact = request.GET.get('primarycontact')
            lead = lead_management.objects.filter(primarycontact=primarycontact).order_by('enquirydate').first()
            
            if lead:
                data = {
                    'sourceoflead': lead.sourceoflead,
                    'salesperson': lead.salesperson,
                    'customername': lead.customername,
                    'customersegment': lead.customersegment,
                    'enquirydate': lead.enquirydate.strftime('%Y-%m-%d') if lead.enquirydate else '',
                    'contactedby': lead.contactedby,
                    'maincategory': lead.maincategory,
                    'subcategory': lead.subcategory,
                    'secondarycontact': lead.secondarycontact,
                    'customeremail': lead.customeremail,
                    'customeraddress': lead.customeraddress,
                    'location': lead.location,
                    'state': lead.state,
                    'city': lead.city,
                    'branch': lead.branch,
                    'typeoflead': lead.typeoflead,
                    'firstfollowupdate': lead.firstfollowupdate.strftime('%Y-%m-%d') if lead.firstfollowupdate else '',
                }
                return JsonResponse({'status': 'exists', 'data': data})
            else:
                return JsonResponse({'status': 'not_found'})

        return render(request, 'lead_management.html', {'salespersons': salespersons})

    else:  # POST request
        try:
            # Get all form data
            sourceoflead = request.POST.get('sourceoflead')
            salesperson = request.POST.get('salesperson')
            customername = request.POST.get('customername')
            customersegment = request.POST.get('customersegment')
            
            # Handle date fields
            enquirydate_str = request.POST.get('enquirydate')
            enquirydate = datetime.strptime(enquirydate_str, '%Y-%m-%d').date() if enquirydate_str else None
            
            contactedby = request.POST.get('contactedby')
            maincategory = request.POST.get('maincategory')
            subcategory = request.POST.get('subcategory')

            # Handle phone numbers
            primarycontact = request.POST.get('primarycontact')
            primarycontact = int(primarycontact) if primarycontact and primarycontact.isdigit() else None
            
            secondarycontact = request.POST.get('secondarycontact')
            secondarycontact = int(secondarycontact) if secondarycontact and secondarycontact.isdigit() else None

            # Other fields
            customeremail = request.POST.get('customeremail')
            customeraddress = request.POST.get('customeraddress')
            location = request.POST.get('location')
            city = request.POST.get('city', 'Unknown City')
            state = request.POST.get('state')
            typeoflead = request.POST.get('typeoflead')
            
            firstfollowupdate_str = request.POST.get('firstfollowupdate')
            firstfollowupdate = datetime.strptime(firstfollowupdate_str, '%Y-%m-%d').date() if firstfollowupdate_str else None
            
            branch = request.POST.get('branch')

            # Create new lead (duplicates allowed)
            lead = lead_management.objects.create(
                sourceoflead=sourceoflead,
                salesperson=salesperson,
                customername=customername,
                customersegment=customersegment,
                enquirydate=enquirydate,
                contactedby=contactedby,
                maincategory=maincategory,
                subcategory=subcategory,
                primarycontact=primarycontact,
                secondarycontact=secondarycontact,
                customeremail=customeremail,
                customeraddress=customeraddress,
                location=location,
                state=state,
                city=city,
                branch=branch,
                typeoflead=typeoflead,
                firstfollowupdate=firstfollowupdate,
            )

            return redirect('/display_lead_management')

        except Exception as e:
            # Log the error for debugging
            print(f"Error creating lead: {str(e)}")
            # Return the user to the form with error message
            return render(request, 'lead_management.html', {
                'salespersons': salespersons,
                'error': 'There was an error submitting the form. Please try again.'
            })



from django.shortcuts import render, get_object_or_404, redirect
from .models import lead_management, main_followup
from django.utils import timezone

def main_followup_view(request, lead_id):
    lead = get_object_or_404(lead_management, id=lead_id)
    followups = main_followup.objects.filter(lead=lead).order_by('created_at')
    followup_count = followups.count() + 1

    latest_followup = followups.last()

    if request.method == "POST":
        done_pest_control = request.POST.get('done_pest_control', 'No')
        agency_name = request.POST.get('agency_name') if done_pest_control == 'Yes' else None
        onsite_infestation = request.POST.get('onsite_infestation', '')
        infestation_level = request.POST.get('infestation_level', '')
        typeoflead = request.POST.get('typeoflead', '')
        followup_remark = request.POST.get('followup_remark', '')
        followup_comment = request.POST.get('followup_comment', '')
        order_status = request.POST.get('order_status', 'Not Closed')
        next_followup_date = (
            request.POST.get('next_followup_date')
            if order_status not in ['Close Win', 'Close Loss'] else None
        )

        if latest_followup:
            # Update existing follow-up
            latest_followup.done_pest_control = done_pest_control
            latest_followup.agency_name = agency_name
            latest_followup.onsite_infestation = onsite_infestation
            latest_followup.infestation_level = infestation_level
            latest_followup.typeoflead = typeoflead
            latest_followup.followup_remark = followup_remark
            latest_followup.followup_comment = followup_comment
            latest_followup.next_followup_date = next_followup_date
            latest_followup.order_status = order_status
            latest_followup.save()
        else:
            # Create new follow-up if none exists
            main_followup.objects.create(
                lead=lead,
                done_pest_control=done_pest_control,
                agency_name=agency_name,
                onsite_infestation=onsite_infestation,
                infestation_level=infestation_level,
                typeoflead=typeoflead,
                followup_remark=followup_remark,
                followup_comment=followup_comment,
                next_followup_date=next_followup_date,
                order_status=order_status,
                created_at=timezone.now(),
            )

        # Update the lead's status
       # Update the lead's status
        lead.typeoflead = typeoflead
        main_followup.order_status = order_status  # ✅ important to reflect in lead model
        if order_status in ['Close Win', 'Close Loss']:
            lead.stage = 0  # mark lead as closed
        lead.save()


        return redirect('today_work')

    context = {
        'lead': lead,
        'followup_count': followup_count,
        'followups': followups,
        'previous_followup': latest_followup,
        
    }
    return render(request, 'main_followup.html', context)







from django.shortcuts import render
from .models import main_followup, lead_management
from django.utils import timezone
from datetime import date
from django.core.paginator import Paginator
from itertools import chain

def today_work(request):
    today = date.today()

    print("today",today)
    salesperson_filter = request.GET.get('salesperson')

    # Filter today's follow-ups
    lead_folloup = lead_management.objects.filter(firstfollowupdate = today)
    followups = main_followup.objects.filter(next_followup_date=today).select_related('lead')

    if salesperson_filter:
        followups = followups.filter(lead__salesperson=salesperson_filter)
        lead_folloup = lead_folloup.filter(lead__salesperson=salesperson_filter)

    # Combine followups and lead_folloup
    combined = list(chain(
        followups,  # main_followup objects (with .lead field)
        [lead for lead in lead_folloup if not main_followup.objects.filter(lead=lead).exists()]  # avoid duplication
    ))
    
    print("combined", combined)
    # Pagination
    paginator = Paginator(combined, 10)  # Show 10 records per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all unique salespersons
    salespersons = lead_management.objects.values_list('salesperson', flat=True).distinct()

    # Used for correct indexing
    start_index = (page_obj.number - 1) * paginator.per_page


    return render(request, 'today_work.html', {
        'page_obj': page_obj,
        'salespersons': salespersons,
        'selected_salesperson': salesperson_filter,
        'start_index': start_index
    })



from datetime import date

def pending_followups(request):
    today = date.today()
    salesperson_filter = request.GET.get('salesperson')

    # Get followups with a past next_followup_date
    lead_folloup = lead_management.objects.filter(firstfollowupdate__lt = today)
    followups = main_followup.objects.filter(next_followup_date__lt=today).select_related('lead')

    if salesperson_filter:
        followups = followups.filter(lead__salesperson=salesperson_filter)
        lead_folloup = lead_folloup.filter(lead__salesperson=salesperson_filter)

    combined = list(chain(
           followups,  # main_followup objects (with .lead field)
           [lead for lead in lead_folloup if not main_followup.objects.filter(lead=lead).exists()]  # avoid duplication
       ))
    # Pagination
    paginator = Paginator(combined, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    salespersons = lead_management.objects.values_list('salesperson', flat=True).distinct()
    start_index = (page_obj.number - 1) * paginator.per_page

    return render(request, 'pending_followups.html', {
        'page_obj': page_obj,
        'salespersons': salespersons,
        'selected_salesperson': salesperson_filter,
        'start_index': start_index
    })




# In crmapp/views.py

from django.shortcuts import render
from .models import lead_management, firstfollowup, secondfollowup, thirdfollowup, finalfollowup


from django.db.models import Q  # For complex queries

def display_followup(request):
    search_query = request.GET.get('q', '')  # Get the search query
    
    leads = lead_management.objects.all()
    if search_query:
        leads = leads.filter(
            Q(customername__icontains=search_query) |  # Search by customer name
            Q(customeremail__icontains=search_query)  # Optionally, search by email
        )
    
    followups = []
    for lead in leads:
        followups.append({
            "lead": lead,
            "firstfollowup": firstfollowup.objects.filter(lead=lead).first(),
            "secondfollowup": secondfollowup.objects.filter(lead=lead).first(),
            "thirdfollowup": thirdfollowup.objects.filter(lead=lead).first(),
            "finalfollowup": finalfollowup.objects.filter(lead=lead).first(),
        })
    
    context = {
        "followups": followups,
        "search_query": search_query,
    }
    return render(request, 'display_followup.html', context)

def fetch_customer_details(request, customer_id):
    customer = get_object_or_404(customer_details, customerid=customer_id)
    return render(request, 'customer_details_modal.html', {'customer': customer})


def display_customer(request):
    query = request.GET.get('search', '')
    sort_order = request.GET.get('order', 'asc')
    sort_by = request.GET.get('sort_by', 'customerid')

    if query:
        m = (customer_details.objects.filter(customerid__icontains=query) |
             customer_details.objects.filter(primarycontact__icontains=query))
    else:
        m = customer_details.objects.all()

    if sort_by == 'firstname':
        if sort_order == 'desc':
            m = m.order_by('-firstname')  
        else:
            m = m.order_by('firstname')  
    else:
        if sort_order == 'desc':
            m = m.order_by('-customerid')  
        else:
            m = m.order_by('customerid')

    paginator = Paginator(m, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'current_order': sort_order,
        'current_sort_by': sort_by,
        'page_obj': page_obj,
        'start_index': start_index,
        'data': page_obj.object_list,  
    }

    return render(request, 'display_customer.html', context)


from crmapp.models import Reschedule
def display_reschedule(request):
    query = request.GET.get('search', '').strip()
    sort_order = request.GET.get('order', 'asc')
    sort_by = request.GET.get('sort_by', 'customerid')
    
    if query:
        # Filter results by customer ID or service ID
        m = Reschedule.objects.filter(
            service__customer__customerid__icontains=query
        ) | Reschedule.objects.filter(
            service__id__icontains=query
        )
    else:
        # Display all records if no search query
        m = Reschedule.objects.all()

    if sort_by == 'service_id':
        if sort_order == 'desc':
            m = m.order_by('-service__id')  
        else:
            m = m.order_by('service__id')  
    else:
        if sort_order == 'desc':
            m = m.order_by('-service__customer__customerid')  
        else:
            m = m.order_by('service__customer__customerid')

    paginator = Paginator(m, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'page_obj': page_obj,
        'start_index': start_index,
        'search_query': query,
        'current_order': sort_order,
        'current_sort_by': sort_by,
    }

    return render(request, 'display_reschedule.html', context)


def display_service_management(request):
    query = request.GET.get('search', '')
    sort_order = request.GET.get('order', 'asc')
    sort_by = request.GET.get('sort_by', 'customerid')  
    contract_type = request.GET.get('contract_type', '')

    if query:
        m = service_management.objects.filter(customer__customerid__icontains=query) | service_management.objects.filter(customer__primarycontact__icontains=query)
    else:
        m = service_management.objects.all()

    # Filter by contract type if provided
    if contract_type:
        m = m.filter(contract_type=contract_type)

    # Sorting logic
    if sort_by == 'firstname':
        if sort_order == 'desc':
            m = m.order_by('-customer__firstname')  
        else:
            m = m.order_by('customer__firstname')  
    else:
        if sort_order == 'desc':
            m = m.order_by('-customer__customerid')  
        else:
            m = m.order_by('customer__customerid')

    paginator = Paginator(m, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'current_order': sort_order,
        'current_sort_by': sort_by,
        'page_obj': page_obj,
        'start_index': start_index,
        'contract_type': contract_type,
    }
    context['data'] = m

    return render(request, 'display_service_management.html', context)

def get_service_details(request, service_id):
    service = get_object_or_404(service_management, id=service_id)
    return render(request, 'service_details_modal.html', {'service': service})

def display_allocation(request):
    query = request.GET.get('search', '')
    sort_order = request.GET.get('order', 'asc')
    sort_by = request.GET.get('sort_by', 'customerid')  
    allocated_service_ids = WorkAllocation.objects.values_list('service_id', flat=True)
    
    if query:
        m = service_management.objects.filter(
            customer__customerid__icontains=query
        ) | service_management.objects.filter(
            customer__primarycontact__icontains=query
        )
    else:
        m = service_management.objects.all()

    if sort_by == 'firstname':
        if sort_order == 'desc':
            m = m.order_by('-customer__firstname')  
        else:
            m = m.order_by('customer__firstname')  
    else:
        if sort_order == 'desc':
            m = m.order_by('-customer__customerid')  
        else:
            m = m.order_by('customer__customerid')

    paginator = Paginator(m, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'allocated_service_ids': list(allocated_service_ids),
        'current_order': sort_order,
        'current_sort_by': sort_by,
        'page_obj': page_obj,
        'start_index': start_index,
    }
    return render(request, 'display_allocation.html', context)

def get_allocation_details(request, service_id):
    allocation = get_object_or_404(service_management, id=service_id)
    return render(request, 'allocation_details_modal.html', {'allocation': allocation})



from django.core.paginator import Paginator
from django.shortcuts import render
from .models import quotation_management

from django.core.paginator import Paginator

def display_quotation(request):
    query = request.GET.get('search', '')
    sort_order = request.GET.get('order', 'asc')
    sort_order = sort_order if sort_order in ['asc', 'desc'] else 'asc'
    sort_by = request.GET.get('sort_by', 'customer_full_name')

    valid_sort_fields = ['customer_full_name', 'quotation_date', 'total_price', 'total_price_with_gst']

    m = quotation_management.objects.all()
    if query:
        m = m.filter(customer_full_name__icontains=query)

    if sort_by in valid_sort_fields:
        order_prefix = '-' if sort_order == 'desc' else ''
        m = m.order_by(f'{order_prefix}{sort_by}')
    else:
        m = m.order_by('customer_full_name')

    paginator = Paginator(m, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page
    print(page_obj)
    context = {
        'current_order': sort_order,
        'current_sort_by': sort_by,
        'page_obj': page_obj,
        'start_index': start_index,
        'search_query': query,
    }
    return render(request, 'display_quotation.html', context)


def get_quotation_details(request, quotation_id):
    quotation_var = get_object_or_404(quotation, id=quotation_id)
    return render(request, 'quotation_details_modal.html', {'quotation_var': quotation_var})

def display_invoice(request):
    query = request.GET.get('search', '')
    sort_order = request.GET.get('order', 'asc')
    sort_by = request.GET.get('sort_by', 'customerid')  
    
    if query:
        m = invoice.objects.filter(customer__customerid__icontains=query) & invoice.objects.filter(invoice_no__icontains=query)
    else:
        m = invoice.objects.all()
    
    if sort_by == 'firstname':
        if sort_order == 'desc':
            m = m.order_by('-customer__firstname')  
        else:
            m = m.order_by('customer__firstname')  
    else:
        if sort_order == 'desc':
            m = m.order_by('-customer__customerid')  
        else:
            m = m.order_by('customer__customerid')

    paginator = Paginator(m, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'current_order': sort_order,
        'current_sort_by': sort_by,
        'page_obj': page_obj,
        'start_index': start_index,
    }
    return render(request, 'display_invoice.html', context)


def get_invoice_details(request, invoice_id):
    invoice_var = get_object_or_404(invoice, id=invoice_id)
    return render(request, 'invoice_details_modal.html', {'invoice_var': invoice_var})





from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.db.models.functions import Lower
from .models import lead_management, SalesPerson
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from django.core.paginator import Paginator
from .models import lead_management, SalesPerson, main_followup


def display_lead_management(request):
    # 1. Start with all leads
    filtered_leads = lead_management.objects.all()

    # 2. Get filters from request
    search_query = request.GET.get('search', '').strip()
    typeoflead_filter = request.GET.get('typeoflead')
    source_filter = request.GET.get('sourceoflead')
    salesperson_filter = request.GET.get('salesperson')
    branch_filter = request.GET.get('branch')
    enquiry_from = request.GET.get('enquiry_from')
    enquiry_to = request.GET.get('enquiry_to')
    followup_from = request.GET.get('followup_from')
    followup_to = request.GET.get('followup_to')
    sort_by = request.GET.get('sort', 'customername')
    order = request.GET.get('order', 'asc')

    # 3. Apply search filter
    if search_query:
        filtered_leads = filtered_leads.filter(
            Q(primarycontact__icontains=search_query) |
            Q(typeoflead__icontains=search_query) |
            Q(customername__icontains=search_query)
        )

    # 4. Apply other filters
    if typeoflead_filter:
        filtered_leads = filtered_leads.filter(typeoflead=typeoflead_filter)
    if source_filter:
        filtered_leads = filtered_leads.filter(sourceoflead=source_filter)
    if salesperson_filter:
        filtered_leads = filtered_leads.filter(salesperson=salesperson_filter)
    if branch_filter:
        filtered_leads = filtered_leads.filter(branch=branch_filter)
    if enquiry_from and enquiry_to:
        filtered_leads = filtered_leads.filter(enquirydate__range=[enquiry_from, enquiry_to])
    if followup_from and followup_to:
        filtered_leads = filtered_leads.filter(firstfollowupdate__range=[followup_from, followup_to])

    # 5. Count for display
    branch_count = filtered_leads.count()

    # 6. Apply sorting
    order_prefix = '-' if order == 'desc' else ''
    leads = filtered_leads.order_by(f'{order_prefix}{sort_by}')

    # 7. Apply pagination
    paginator = Paginator(leads, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    start_index = (page_obj.number - 1) * paginator.per_page

    # 8. Prepare followup data
    lead_ids = [lead.id for lead in page_obj]
    followups = main_followup.objects.filter(lead_id__in=lead_ids).order_by('lead_id', '-created_at')

    latest_followups = {}
    for followup in followups:
        if followup.lead_id not in latest_followups:
            latest_followups[followup.lead_id] = followup

    # Attach the latest follow-up to each lead
    for lead in page_obj:
        lead.latest_followup = latest_followups.get(lead.id)
        

    # 9. Get dropdown filter values
    typeoflead_choices = [choice[0] for choice in lead_management._meta.get_field('typeoflead').choices if choice[0]]
    typeoflead_used = lead_management.objects.values_list('typeoflead', flat=True).distinct()
    lead_types = sorted(set(typeoflead_choices + list(typeoflead_used)))

    source_choices = [choice[0] for choice in lead_management._meta.get_field('sourceoflead').choices if choice[0]]
    source_used = lead_management.objects.values_list('sourceoflead', flat=True).distinct()
    sources = sorted(set(source_choices + list(source_used)))

    branch_choices = [choice[0] for choice in lead_management._meta.get_field('branch').choices if choice[0]]
    branch_used = lead_management.objects.values_list('branch', flat=True).distinct()
    branches = sorted(set(branch_choices + list(branch_used)))

    salespersons = SalesPerson.objects.values_list('full_name', flat=True).distinct()

    # 10. No data message if needed
    no_data_message = ""
    if not leads.exists():
        if search_query:
            no_data_message = f"No data found for search: {search_query}"
        elif typeoflead_filter:
            no_data_message = f"No data found for Type of Lead: {typeoflead_filter}"
        elif source_filter:
            no_data_message = f"No data found for Source of Lead: {source_filter}"
        elif salesperson_filter:
            no_data_message = f"No data found for Salesperson: {salesperson_filter}"
        elif branch_filter:
            no_data_message = f"No data found for Branch: {branch_filter}"
        else:
            no_data_message = "No data found for the selected filters."

    # 11. Final context
    context = {
        'page_obj': page_obj,
        'start_index': start_index,
        'lead_types': lead_types,
        'sources': sources,
        'branches': branches,
        'salespersons': salespersons,
        'search_query': search_query,
        'current_sort': sort_by,
        'current_order': order,
        'no_data_message': no_data_message,
        'branch_count': branch_count,
    }

    return render(request, 'display_lead_management.html', context)



from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
import xlwt

def export_leads_excel(request):
    from .models import lead_management

    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename="leads_full.xls"'

    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet('Leads')

    # Get all model field names
    model_fields = [field.name for field in lead_management._meta.fields]

    # Write header
    for col_num, field_name in enumerate(model_fields):
        ws.write(0, col_num, field_name.replace('_', ' ').title())

    # Write data rows
    data = lead_management.objects.all().values_list(*model_fields)
    for row_num, row in enumerate(data, start=1):
        for col_num, cell_value in enumerate(row):
            ws.write(row_num, col_num, str(cell_value))

    wb.save(response)
    return response




def get_lead_details(request, lead_id):
    lead = get_object_or_404(lead_management, id=lead_id)
    return render(request, 'lead_details_modal.html', {'lead': lead})

# Delete Section
# Delete Customer Details

def delete_customer(request , rid):
    
    if request.method == "POST":
        password = request.POST.get("password")
        correct_password = "seva123"  # Replace with the actual password you want to use

        if password == correct_password:
            try:
                m=customer_details.objects.filter(id=rid)
                m.delete()
                messages.success(request, "Record deleted successfully.")
            except customer_details.DoesNotExist:
                messages.error(request, "Record not found.")
        else:
            messages.error(request, "Invalid password. Deletion failed.")

    return redirect('/display_customer')

# Delete Service Management

# def delete_service_management(request , rid):
#     m=service_management.objects.filter(id=rid)

#     m.delete()

#     return redirect('/display_allocation')

# test 1
from django.contrib import messages

def delete_service_management(request, rid):
    if request.method == "POST":
        password = request.POST.get("password")
        correct_password = "seva123"  # Replace with the actual password you want to use

        if password == correct_password:
            try:
                m = service_management.objects.get(id=rid)
                m.delete()
                messages.success(request, "Record deleted successfully.")
            except service_management.DoesNotExist:
                messages.error(request, "Record not found.")
        else:
            messages.error(request, "Invalid password. Deletion failed.")

    return redirect('/display_allocation')


# Delete Quotation

def delete_quotation(request , rid):
    if request.method == "POST":
        password = request.POST.get("password")
        correct_password = "seva123"  # Replace with the actual password you want to use

        if password == correct_password:
            try:
                m=quotation.objects.filter(id=rid)
                m.delete()
                messages.success(request, "Record deleted successfully.")
            except quotation.DoesNotExist:
                messages.error(request, "Record not found.")
        else:
            messages.error(request, "Invalid password. Deletion failed.")

    return redirect('/display_quotation')

# Delete Invoice

def delete_invoice(request , rid):
    if request.method == "POST":
        password = request.POST.get("password")
        correct_password = "seva123"  # Replace with the actual password you want to use

        if password == correct_password:
            try:
                m=invoice.objects.filter(id=rid)
                m.delete()
                messages.success(request, "Record deleted successfully.")
            except invoice.DoesNotExist:
                messages.error(request, "Record not found.")
        else:
            messages.error(request, "Invalid password. Deletion failed.")

    return redirect('/display_invoice')


# Delete Inventory

# def delete_inventory(request , rid):
#     m=inventory.objects.filter(id=rid)

#     m.delete()

#     return redirect('/display_inventory')


# Delete Lead Management

def delete_lead_management(request , rid):
    if request.method == "POST":
        password = request.POST.get("password")
        correct_password = "seva123"  # Replace with the actual password you want to use

        if password == correct_password:
            try:
                m=lead_management.objects.filter(id=rid)
                m.delete()
                messages.success(request, "Record deleted successfully.")
            except lead_management.DoesNotExist:
                messages.error(request, "Record not found.")
        else:
            messages.error(request, "Invalid password. Deletion failed.")

    return redirect('/display_lead_management')



# Edit Section

# Edit Customer Details

def edit_customer(request , rid):
    

    if request.method =='GET':

        m=customer_details.objects.filter(id=rid)

        context={}
        context['data']=m
    
        return render(request , 'edit_customer.html' , context)
    
    else:
        ufirstname=request.POST['ufirstname']
        ulastname=request.POST['ulastname']
        uprimaryemail=request.POST['uprimaryemail']
        usecondaryemail=request.POST['usecondaryemail']
        uprimarycontact=request.POST['uprimarycontact']
        usecondarycontact=request.POST['usecondarycontact']
        if not usecondarycontact:
            usecondarycontact = None
        ucontactperson=request.POST['ucontactperson']
        ucustomersegment=request.POST['ucustomersegment']
        ushifttopartyaddress=request.POST['ushifttopartyaddress']
        ushifttopartycity=request.POST['ushifttopartycity']
        ushifttopartystate=request.POST['ushifttopartystate']
        ushifttopartypostal=request.POST['ushifttopartypostal']
        usoldtopartyaddress=request.POST['usoldtopartyaddress']
        usoldtopartycity=request.POST['usoldtopartycity']
        usoldtopartystate=request.POST['usoldtopartystate']
        usoldtopartypostal=request.POST['usoldtopartypostal']
        

        m=customer_details.objects.filter(id=rid)

        m.update(firstname=ufirstname, lastname=ulastname , primaryemail=uprimaryemail,  secondaryemail=usecondaryemail , primarycontact=uprimarycontact , secondarycontact=usecondarycontact , contactperson=ucontactperson , customersegment=ucustomersegment , shifttopartyaddress=ushifttopartyaddress , shifttopartycity=ushifttopartycity , shifttopartystate=ushifttopartystate , shifttopartypostal=ushifttopartypostal , soldtopartyaddress=usoldtopartyaddress , soldtopartycity=usoldtopartycity , soldtopartystate=usoldtopartystate , soldtopartypostal=usoldtopartypostal)

       
        return redirect( '/display_customer')
    




# Edit Service Management

# from datetime import datetime
# def edit_service_management(request , rid):

#     if request.method =='GET':

#         m=service_management.objects.filter(id=rid)

#         context={}
#         context['data']=m
    
#         return render(request , 'edit_service_management.html' , context)  
#     else:
#         upestcontrolservice=request.POST['upestcontrolservice']
#         uservices=request.POST['uservices']
#         uservicetype=request.POST['uservicetype']
#         uservice_frequency=request.POST['uservice_frequency']
#         uservice_charges=request.POST['uservice_charges']

#         if 'ugst_checkbox' in request.POST:
#             ugst_checkbox = True
#         else:
#             ugst_checkbox = False

#         upayment_terms_checkbox = request.POST.get('upayment_terms_checkbox')
#         uservice_date_str=request.POST['uservice_date']
#         ulead_date_str=request.POST['ulead_date']
#         usales_person_name=request.POST['usales_person_name']
#         usales_person_contact_no=request.POST['usales_person_contact_no']
#         utechnician_operator_name=request.POST['utechnician_operator_name']

#         try:
#             uservice_date = datetime.strptime(uservice_date_str, '%Y-%m-%d').date()
#         except ValueError:
#             uservice_date = None
        
#         try:
#             ulead_date = datetime.strptime(ulead_date_str, '%Y-%m-%d').date()
#         except ValueError:
#             ulead_date = None

#         if ugst_checkbox:
#             total_charges = float(uservice_charges) * 1.18  # Adding 18% GST
#             upayment_terms_checkbox = "Payment Due in 15 days (including GST)"
#         else:
#             total_charges = float(uservice_charges)
#             upayment_terms_checkbox = "100% Advance Payment"

        
        

#         m=service_management.objects.filter(id=rid)

#         m.update(pestcontrolservice=upestcontrolservice, services=uservices , servicetype=uservicetype, service_frequency=uservice_frequency , service_charges=uservice_charges , gst_checkbox = True if ugst_checkbox == 'on' else False , payment_terms_checkbox=upayment_terms_checkbox , service_date=uservice_date , lead_date=ulead_date , sales_person_name=usales_person_name , sales_person_contact_no=usales_person_contact_no , technician_operator_name=utechnician_operator_name , total_charges=total_charges)

       
#         return redirect( '/display_service_management')
from .models import Reschedule
from datetime import datetime
def edit_service_management(request, rid):
    if request.method == 'GET':
        service_obj = get_object_or_404(service_management, id=rid)
        previous_reschedules = Reschedule.objects.filter(service_id=rid)
        all_technicians = TechnicianProfile.objects.all()

        # Get users already assigned as technicians (via TechWorkList)
        allocated_technicians = User.objects.filter(techworklist__service=service_obj).distinct()
   
        context = {
            'data': [service_obj],
            'previous_reschedules': previous_reschedules,
            'technicians': all_technicians,
            'selected_technicians': allocated_technicians,
        }

        return render(request, 'edit_service_management.html', context)

    else:
        service_obj = get_object_or_404(service_management, id=rid)

        technician_ids = request.POST.getlist('technicians')
        print("technician_ids :", technician_ids)
        ucustomer_id = request.POST.get('ucustomer')
        uaddress = request.POST.get('uaddress')
        utotal_price = float(request.POST['utotal_price'])
        utotal_price_with_gst = float(request.POST['utotal_price_with_gst'])
        ucontract_type = request.POST.get('ucontract_type')
        ucontract_status = request.POST.get('ucontract_status')
        uproperty_type = request.POST.get('uproperty_type')
        uwarranty_period = request.POST.get('uwarranty_period')
        ustate = request.POST.get('ustate')
        ucity = request.POST.get('ucity')
        upincode = request.POST.get('upincode')
        ugps_location = request.POST.get('ugps_location')
        ufrequency_count = request.POST.get('ufrequency_count')
        upayment_terms = request.POST.get('upayment_terms')
        usales_person_name = request.POST.get('usales_person_name')
        usales_person_contact_no = request.POST.get('usales_person_contact_no')
        udelivery_time = request.POST.get('udelivery_time')
        ulead_date = request.POST['ulead_date']
        uservice_date = request.POST['uservice_date']
        udescription = request.POST.get('work_description')
        upayment_status = request.POST.get('customer_payment_status')

        # Step 1: Ensure WorkAllocation exists for the service
        work_allocation, created = WorkAllocation.objects.get_or_create(
            service=service_obj,
            defaults={
                'fullname': service_obj.customer.fullname,
                'customer_contact': service_obj.customer.primarycontact,
                'customer_address': service_obj.address,
                'work_description': udescription or "Updated work",
                'customer_payment_status': upayment_status or "Pending",
                'payment_amount': service_obj.total_price_with_gst,
                'gps_location': service_obj.gps_location,
            }
        )

        # Step 2: Delete old TechWorkList entries
        TechWorkList.objects.filter(service=service_obj).delete()
        # Step 3: Assign new technicians
        technician_profiles = TechnicianProfile.objects.filter(id__in=technician_ids)
        work_allocation.technician.set(technician_profiles)  # update technicians for WorkAllocation

        for tech_profile in technician_profiles:
            tech_user = tech_profile.user  # convert to User model
            tech_work = TechWorkList.objects.create(
                technician=tech_user,
                service=service_obj,
            )
            tech_work.work.add(work_allocation)


        # Step 4: Update service fields
        try:
            customer = customer_details.objects.get(customerid=ucustomer_id)
        except customer_details.DoesNotExist:
            return HttpResponse("Customer not found")

        service_obj.customer = customer
        service_obj.address = uaddress
        service_obj.total_price = utotal_price
        service_obj.total_price_with_gst = utotal_price_with_gst
        service_obj.contract_type = ucontract_type
        service_obj.contract_status = ucontract_status
        service_obj.property_type = uproperty_type
        service_obj.warranty_period = uwarranty_period
        service_obj.state = ustate
        service_obj.city = ucity
        service_obj.pincode = upincode
        service_obj.gps_location = ugps_location
        service_obj.frequency_count = ufrequency_count
        service_obj.payment_terms = upayment_terms
        service_obj.sales_person_name = usales_person_name
        service_obj.sales_person_contact_no = usales_person_contact_no
        service_obj.delivery_time = udelivery_time
        service_obj.lead_date = ulead_date
        service_obj.service_date = uservice_date
        service_obj.technicians.set(technician_ids)
        service_obj.save()

        return redirect('/display_allocation')

# Edit Quotation

# new try
def edit_quotation(request, rid):
    if request.method == 'GET':
        m = quotation.objects.filter(id=rid)
        context = {'data': m}
        return render(request, 'edit_quotation.html', context)
    
    else:
        ucustomer_id = request.POST.get('ucustomer')
        uquantity = int(request.POST['uquantity'])
        uprice = float(request.POST['uprice'])
        utermsandcondition = request.POST['utermsandcondition']
        uservicetype_q = request.POST['uservicetype_q']
        utotal_amount = float(request.POST['hidden_total_amount'])  # Use hidden input value
        utotal_amount_with_gst = float(request.POST['hidden_total_amount_with_gst'])  # Use hidden input value
        udiscount = float(request.POST['udiscount']) if request.POST['udiscount'] else None
        ugst_checkbox = 'ugst' in request.POST  # Check for the GST checkbox
        ucompany_name = request.POST.get('ucompany_name')
        ucompany_email = request.POST.get('ucompany_email')
        ucompany_contact_no = request.POST.get('ucompany_contact_no')
        uquotation_date = request.POST.get('uquotation_date')

        try:
            uquotation_date = datetime.strptime(uquotation_date, '%Y-%m-%d').date() if uquotation_date else timezone.now().date()
        except ValueError:
            uquotation_date = None

        ucompany_address = request.POST.get('ucompany_address')
        usubject = request.POST.get('usubject')
        
        try:
            customer = customer_details.objects.get(customerid=ucustomer_id)
        except customer_details.DoesNotExist:
            return HttpResponse("Customer not found")

        # Fetch the latest quotation for the customer and increment the version
        latest_quotation = quotation.objects.filter(customer=customer,servicetype_q=uservicetype_q).order_by('-version').first()
        new_version = latest_quotation.version + 1 if latest_quotation else 1

        # Update the existing quotation and mark it inactive
        m = quotation.objects.filter(id=rid)
        m.update(status='inactive')

        # Update the quotation details with new values
        m.update(
            customer=customer,
            quantity=uquantity,
            price=uprice,
            termsandcondition=utermsandcondition,
            servicetype_q=uservicetype_q,
            discount=udiscount,
            total_amount=utotal_amount,
            company_name=ucompany_name,
            company_email=ucompany_email,
            company_contact_no=ucompany_contact_no,
            quotation_date=uquotation_date,
            company_address=ucompany_address,
            subject=usubject,
            total_amount_with_gst=utotal_amount_with_gst,
            gst_checkbox=ugst_checkbox,
            version=new_version,
            status='active'
        )
       
        return redirect('/display_quotation')


# Edit Invoice



def edit_invoice(request , rid):

    if request.method =='GET':

        m=invoice.objects.filter(id=rid)

        context={}
        context['data']=m
    
        return render(request , 'edit_invoice.html' , context)
    
    else: 
        umodeofpayment = request.POST['umodeofpayment']
        udispatchedthrough = request.POST['udispatchedthrough']
        utermofdelivery = request.POST['utermofdelivery']
        utermsandcondition = request.POST['utermsandcondition']
        ucompany_name = request.POST['ucompany_name']
        ucompany_email = request.POST['ucompany_email']
        ucompany_contact_no = request.POST['ucompany_contact_no']
        # uinvoice_no = request.POST['uinvoice_no']
       
        udescription_of_goods = request.POST['udescription_of_goods']
        uhsn_sac_code = request.POST['uhsn_sac_code']
        uquantity = int(request.POST['uquantity'])
        uprice = float(request.POST['uprice'])
        udiscount =  float(request.POST['udiscount']) if request.POST['udiscount'] else None
        ugst_checkbox = True if 'ugst_checkbox' in request.POST else False
        utotal_amount = request.POST['utotal_amount']
        utotal_amount_with_gst = request.POST['utotal_amount_with_gst']
        utotal_amount_in_words = request.POST['utotal_amount_in_words']
        upan_card_no = request.POST['upan_card_no']
        uaccount_no = request.POST['uaccount_no']
        ubranch = request.POST['ubranch']
        uifsc_code = request.POST['uifsc_code']
        udispatched_date_str = request.POST['udelivery_date']
        udelivery_date_str = request.POST['udispatched_date']

        try:
            udispatched_date = datetime.strptime(udispatched_date_str, '%Y-%m-%d').date() if udispatched_date_str else timezone.now().date()
        except ValueError:
            udispatched_date = None  # Handle invalid date format
        
        try:
            udelivery_date = datetime.strptime(udelivery_date_str, '%Y-%m-%d').date() if udelivery_date_str else timezone.now().date()
        except ValueError:
            udelivery_date = None  # Handle invalid date format

        utotal_amount = uquantity * uprice
        
        udiscounted_amount = utotal_amount - (utotal_amount * (udiscount / 100))
        utotal_amount_with_gst = udiscounted_amount * 1.18 if ugst_checkbox else udiscounted_amount

       
        

        m=invoice.objects.filter(id=rid)

        m.update(modeofpayment=umodeofpayment, dispatchedthrough=udispatchedthrough , termofdelivery=utermofdelivery,  termsandcondition=utermsandcondition , company_name=ucompany_name , company_email=ucompany_email , company_contact_no=ucompany_contact_no  , dispatched_date=udispatched_date, description_of_goods=udescription_of_goods,hsn_sac_code=uhsn_sac_code ,quantity =uquantity,price=uprice, discount=udiscount, gst_checkbox=ugst_checkbox,total_amount=utotal_amount ,total_amount_with_gst =utotal_amount_with_gst, total_amount_in_words=utotal_amount_in_words ,pan_card_no=upan_card_no , account_no=uaccount_no , branch=ubranch ,ifsc_code=uifsc_code ,delivery_date =udelivery_date )

       
        return redirect( '/display_invoice')



# Edit Inventory



# def edit_inventory(request , rid):

#     if request.method =='GET':

#         m=inventory.objects.filter(id=rid)

#         context={}
#         context['data']=m
    
#         return render(request , 'edit_inventory.html' , context)
    
#     else:
#         uitemnumber=request.POST['uitemnumber']
#         uitemname=request.POST['uitemname']
#         uprice=request.POST['uprice']
#         uquantity=request.POST['uquantity']
       
        

#         m=inventory.objects.filter(id=rid)

#         m.update(itemnumber=uitemnumber, itemname=uitemname , price=uprice,  quantity=uquantity)

       
#         return redirect( '/display_inventory')
    


# Edit Lead Management


from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import datetime
from .models import lead_management

def edit_lead_management(request, rid):
    if request.method =='GET':

        m=lead_management.objects.filter(id=rid)

        context={}
        context['data']=m
    
        return render(request , 'edit_lead_management.html' , context)
    
    elif request.method == 'POST':
        usourceoflead = request.POST.get('usourceoflead', '')
        usalesperson = request.POST.get('usalesperson', '')
        ucustomername = request.POST.get('ucustomername', '')
        ucustomersegment = request.POST.get('ucustomersegment', '')
        utypeoflead = request.POST.get('utypeoflead', '')
        ucontactedby = request.POST.get('ucontactedby', '')
        uenquirydate = request.POST.get('uenquirydate', '')

        try:
            uenquirydate = datetime.strptime(uenquirydate, '%Y-%m-%d').date() if uenquirydate else timezone.now().date()
        except ValueError:
            uenquirydate = None  # Handle invalid date format

        umaincategory = request.POST.get('umaincategory', '')
        usubcategory = request.POST.get('usubcategory', '')
        uprimarycontact = request.POST.get('uprimarycontact', '')
        usecondarycontact = request.POST.get('usecondarycontact', '')
        ucustomeremail = request.POST.get('ucustomeremail', '')
        ucustomeraddress = request.POST.get('ucustomeraddress', '')
        ulocation = request.POST.get('ulocation', '')       
        ucity = request.POST.get('ucity', '')
        ufirstfollowupdate = request.POST.get('ufirstfollowupdate', '')

        try:
            ufirstfollowupdate = datetime.strptime(ufirstfollowupdate, '%Y-%m-%d').date() if ufirstfollowupdate else timezone.now().date()
        except ValueError:
            ufirstfollowupdate = None  # Handle invalid date format

        m=lead_management.objects.filter(id=rid)

        m.update(
            sourceoflead = usourceoflead,
            salesperson = usalesperson,
            customername = ucustomername,
            customersegment = ucustomersegment,
            typeoflead = utypeoflead,
            contactedby = ucontactedby,
            enquirydate = uenquirydate,
            maincategory = umaincategory,
            subcategory = usubcategory,
            primarycontact = uprimarycontact,
            secondarycontact = usecondarycontact,
            customeremail = ucustomeremail,
            customeraddress = ucustomeraddress,
            location = ulocation,
            city = ucity,
            firstfollowupdate=ufirstfollowupdate
        )
        
       
        return redirect('/display_lead_management')



 
def search_inventory(request):
    query = request.GET.get('q', '')
    if query:
        results = Inventory_summary.objects.filter(
            Q(customerid__icontains=query) | Q(customername__icontains=query)
        )
    else:
        results = Inventory_summary.objects.all()
    
    return render(request, 'search_inventory.html', {'results': results})



def search(request):
    # search_query = request.GET.get('q', '').strip()
    # if search_query:
    #     # Perform case-insensitive search operation based on the query in the specified fields
    #     results = (
    #         customer_details.objects.filter(firstname__icontains=search_query) |
    #         customer_details.objects.filter(lastname__icontains=search_query) |
    #         customer_details.objects.filter(customerid__icontains=search_query)
    #     )

    #     data = [
    #         {
    #             'customerid': customer.customerid,
    #             'firstname': customer.firstname,
    #             'lastname': customer.lastname,
    #             'primaryemail': customer.primaryemail,
    #             'secondaryemail': customer.secondaryemail,
    #             'primarycontact': customer.primarycontact,
    #             'secondarycontact': customer.secondarycontact,
    #             'contactperson': customer.contactperson,
    #             'customersegment': customer.customersegment,
    #             'shifttopartyaddress': customer.shifttopartyaddress,
    #             'shifttopartycity': customer.shifttopartycity,
    #             'shifttopartystate': customer.shifttopartystate,
    #             'shifttopartypostal': customer.shifttopartypostal,
    #             'soldtopartyaddress': customer.soldtopartyaddress,
    #             'soldtopartycity': customer.soldtopartycity,
    #             'soldtopartystate': customer.soldtopartystate,
    #             'soldtopartypostal': customer.soldtopartypostal,
    #         }
    #         for customer in results
    #     ]

    #     return render(request, 'search.html', {'results': data})
    # else:
    #     return render(request, 'search.html', {'message': 'No search query provided'})



    # search_query = request.GET.get('q', '').strip()
    # sort_field = request.GET.get('sort', 'firstname')  # Default sort field is 'firstname'
    # sort_order = request.GET.get('order', 'asc')  # Default sort order is 'asc'

    # if sort_order == 'desc':
    #     sort_field = f'-{sort_field}'  # Prefix the field with '-' for descending order

    # results = customer_details.objects.all()

    # if search_query:
    #     results = results.filter(
    #         Q(firstname__icontains=search_query) |
    #         Q(lastname__icontains=search_query) |
    #         Q(customerid__icontains=search_query)
    #     )

    # results = results.order_by(sort_field)

    # # Paginate results
    # paginator = Paginator(results, 10)  # Show 10 results per page
    # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_number)

    # context = {
    #     'search_query': search_query,
    #     'page_obj': page_obj,
    #     'sort_order': sort_order,
    #     'sort_field': sort_field.lstrip('-'),  # Remove '-' to pass only field name
    # }

    # return render(request, 'search.html', context)


    # search_query = request.GET.get('q', '').strip()
    # sort_field = request.GET.get('sort', 'firstname')  # Default sorting field
    # sort_order = '' if sort_field.startswith('-') else '-'
    # sort_field = f"{sort_order}{sort_field}"
    
    # if search_query:
    #     # Perform case-insensitive search operation
    #     results = (
    #         customer_details.objects.filter(firstname__icontains=search_query) |
    #         customer_details.objects.filter(lastname__icontains=search_query) |
    #         customer_details.objects.filter(customerid__icontains=search_query)
    #     ).order_by(sort_field)

    #     paginator = Paginator(results, 10)  # Paginate with 10 results per page
    #     page_number = request.GET.get('page', 1)
    #     page_obj = paginator.get_page(page_number)

    #     context = {
    #         'search_query': search_query,
    #         'page_obj': page_obj,
    #         'sort_order': 'asc' if sort_order == '' else 'desc',
    #         'sort_field': sort_field.lstrip('-'),
    #         'no_results': results.exists() == False,  # True if no results found
    #     }
    # else:
    #     context = {
    #         'search_query': search_query,
    #         'page_obj': None,
    #         'sort_order': 'asc',
    #         'sort_field': 'firstname',
    #         'no_results': True,  # True because no query was provided
    #     }

    # return render(request, 'search.html', context)

    search_query = request.GET.get('q', '').strip()
    sort_field = request.GET.get('sort', 'firstname')  # Default sort by 'firstname'
    
    # Determine the sort order
    if sort_field.startswith('-'):
        sort_order = 'desc'
        sort_field = sort_field[1:]  # Remove the '-' to get the actual field name
    else:
        sort_order = 'asc'

    results = customer_details.objects.all()  # Start with all records

    if search_query:
        results = results.filter(
            Q(firstname__icontains=search_query) |
            Q(lastname__icontains=search_query) |
            Q(customerid__icontains=search_query)
        )
    
    # Apply sorting
    results = results.order_by(f"{'-' if sort_order == 'desc' else ''}{sort_field}")

    # Pagination
    paginator = Paginator(results, 10)  # Show 10 results per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'search_query': search_query,
        'page_obj': page_obj,
        'sort_order': sort_order,
        'sort_field': sort_field,
    }

    if not results.exists():
        context['message'] = "No search results found."
    
    return render(request, 'search.html', context)

# In crmapp/views.py
from django.shortcuts import render
from .forms import InventoryServiceForm
from .models import customer_details, Product, Inventory_summary

def inventory_service(request):
    if request.method == 'POST':
        form = InventoryServiceForm(request.POST)
        if form.is_valid():
            customer_id = form.cleaned_data['customer_id']
            customer_name = form.cleaned_data['customer_name']
            product_quantities = {
                form.cleaned_data['p1']: form.cleaned_data['p1_quantity'],
                form.cleaned_data.get('p2'): form.cleaned_data.get('p2_quantity'),
                form.cleaned_data.get('p3'): form.cleaned_data.get('p3_quantity'),
                form.cleaned_data.get('p4'): form.cleaned_data.get('p4_quantity'),
            }

            inventory_entries = []
            total_price = 0

            for product, quantity in product_quantities.items():
                if product and quantity:
                    product_instance = Product.objects.get(product_id=product.product_id)
                    if product_instance.quantity >= quantity:
                        product_instance.quantity -= quantity
                        product_instance.save()

                        inventory_entry = Inventory_summary.objects.create(
                            customer_id=customer_id,
                            customer_name=customer_name,
                            product=product_instance,
                            quantity=quantity,
                            total_price=product_instance.price * quantity
                        )
                        inventory_entries.append(inventory_entry)
                        total_price += inventory_entry.total_price
                    else:
                        return render(request, 'inventory_service.html', {'form': form, 'error': f'Not enough {product_instance.product_name} in stock.'})

            return render(request, 'inventory_summary_result.html', {'customer_id': customer_id, 'customer_name': customer_name, 'inventory_entries': inventory_entries, 'total_price': total_price})
    else:
        form = InventoryServiceForm()
    
    return render(request, 'inventory_service.html', {'form': form})

from django.shortcuts import render
from .models import Inventory_summary, customer_details

def inventory_summary(request):
    customers = customer_details.objects.all()
    inventory_summary = []

    for customer in customers:
        # Filter entries by the correct customer ID
        entries = Inventory_summary.objects.filter(customer_id=customer.customerid)
        
        # Check if entries exist and calculate total price
        if entries.exists():
            total_price = sum(entry.total_price for entry in entries)
        else:
            total_price = 0

        inventory_summary.append({
            'customer': customer,
            'entries': entries,
            'total_price': total_price
        })

    context = {
        'inventory_summary': inventory_summary,
    }
    
    return render(request, 'inventory_summary.html', context)



def add_product(request):
    if request.method == 'POST':
        form = AddProductForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'add_product_success.html')
    else:
        form = AddProductForm()
    return render(request, 'add_product.html', {'form': form})

def update_product(request):
    if request.method == 'POST':
        form = UpdateProductForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data['product']
            price = form.cleaned_data['price']
            add_quantity = form.cleaned_data['add_quantity']

            if price is not None:
                product.price = price
            if add_quantity is not None:
                product.quantity += add_quantity
            product.save()
            return render(request, 'update_product_success.html', {'product': product})
    else:
        form = UpdateProductForm()
    return render(request, 'update_product.html', {'form': form})

@login_required
def create_technician_profile(request):
    if not request.user.is_staff:
        return redirect('not_authorized')

    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        contact_number = request.POST.get('contact_number')
        address = request.POST.get('address')
        city = request.POST.get('city')
        state = request.POST.get('state')
        postal_code = request.POST.get('postal_code')
        date_of_joining = request.POST.get('date_of_joining')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        errors = {}

        if TechnicianProfile.objects.filter(contact_number=contact_number).exists():
            errors['contact_number'] = 'Contact number already exists'

        if TechnicianProfile.objects.filter(email=email).exists():
            errors['email'] = 'Email already exists'

        if User.objects.filter(username=contact_number).exists():
            errors['contact_number'] = 'Contact number (username) already exists'

        if password != confirm_password:
            errors['password'] = 'Passwords do not match'

        if errors:
            return render(request, 'create_technician_profile.html', {
                'errors': errors,
                'form_data': request.POST
            })

        # Create a user account for the technician
        user = User.objects.create_user(
            username=contact_number,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # Create the TechnicianProfile linked to the user
        TechnicianProfile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            contact_number=contact_number,
            address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            date_of_joining=date_of_joining
        )

        return redirect('/index')  # Replace with your success page or URL name

    return render(request, 'create_technician_profile.html')




from django.shortcuts import render, get_object_or_404, redirect
from .models import TechnicianProfile
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.hashers import make_password

from django.shortcuts import render, get_object_or_404, redirect
from .models import TechnicianProfile

# Display technicians with demo passwords
def display_technician(request):
    technicians = TechnicianProfile.objects.all()

    # Manual dictionary to simulate decrypted passwords for each technician
    # This is just for demonstration/testing purposes — do not use in production!
    password_map = {
        tech.id: f"password{tech.id}"  # Replace with actual known plain passwords if you have them
        for tech in technicians
    }

    # Combine technician info with their 'plain' passwords
    technician_data = []
    for tech in technicians:
        technician_data.append({
            'id': tech.id,
            'first_name': tech.first_name,
            'last_name': tech.last_name,
            'email': tech.email,
            'contact_number': tech.contact_number,
            'city': tech.city,
            'date_of_joining': tech.date_of_joining,
            'password': password_map.get(tech.id, 'Unknown')
        })

    return render(request, 'display_technician.html', {'technician_data': technician_data})


# Edit technician
def edit_technician(request, technician_id):
    technician = get_object_or_404(TechnicianProfile, id=technician_id)
    user = technician.user

    if request.method == 'POST':
        technician.first_name = request.POST.get('first_name')
        technician.last_name = request.POST.get('last_name')
        technician.email = request.POST.get('email')
        technician.contact_number = request.POST.get('contact_number')
        technician.address = request.POST.get('address')
        technician.city = request.POST.get('city')
        technician.state = request.POST.get('state')
        technician.postal_code = request.POST.get('postal_code')
        technician.date_of_joining = request.POST.get('date_of_joining')
        password = request.POST.get('password')

        if password:
            user.password = make_password(password)
            user.save()

        technician.save()
        messages.success(request, "Technician updated successfully.")
        return redirect('display_technician')

    return render(request, 'edit_technician.html', {'technician': technician, 'password': user.password})


# Delete technician
def delete_technician(request, technician_id):
    technician = get_object_or_404(TechnicianProfile, id=technician_id)
    user = technician.user
    technician.delete()
    user.delete()
    messages.success(request, "Technician deleted successfully.")
    return redirect('display_technician')


def not_authorized(request):
    return render(request, 'not_authorized.html')


def technician_login(request):
    if request.method == 'POST':
        contact_number = request.POST.get('contact_number')
        password = request.POST.get('password')
        
        user = authenticate(request, username=contact_number, password=password)
        if user is not None:
            login(request, user)
            return redirect('technician_dashboard')
        else:
            return render(request, 'technician_login.html', {'error': 'Invalid login credentials'})

    return render(request, 'technician_login.html')

# @login_required
# def technician_dashboard(request):
#     user = request.user
#     try:
#         technician_profile = TechnicianProfile.objects.get(user=user)
#     except TechnicianProfile.DoesNotExist:
#         technician_profile = None

#     context = {
#         'user': user,
#         'technician_profile': technician_profile,
#     }

#     works = WorkAllocation.objects.all()


#     print('works: ',works)
#     for work in works:
#         if work.status == 'Pending':
#             work.status = 'workdesk'
#             work.save()
#             TechWorkList.objects.create(technician=request.user, work=work)
    
#     return render(request, 'technician_dashboard.html', context)
import json
from django.utils.timezone import now, timedelta
from calendar import monthrange
from django.db.models import Count
from django.utils.timezone import make_aware
from datetime import datetime

@login_required
def technician_dashboard(request):
    user = request.user
    try:
        technician_profile = TechnicianProfile.objects.get(user=user)
    except TechnicianProfile.DoesNotExist:
        technician_profile = None

    # Filter works completed in the past month
    # one_month_ago = now() - timedelta(days=30)
    # works_done_last_month = WorkAllocation.objects.filter(
    #     technician=technician_profile,
    #     allocated_datetime__gte=one_month_ago,
    #     status='Completed'
    # )

    # # Prepare data for the chart
    # work_dates = [work.allocated_datetime.strftime('%Y-%m-%d') for work in works_done_last_month]
    # date_counts = {date: work_dates.count(date) for date in set(work_dates)}

    # chart_data = {
    #     'labels': list(date_counts.keys()),
    #     'data': list(date_counts.values())
    # }

    # chart_data_json = json.dumps(chart_data)

    # Update statuses and create TechWorkList entries

    techworklistobj = TechWorkList.objects.all()
    for i in techworklistobj:
        print('tech',i.technician.first_name,'completion time',i.completion_datetime )


    works = WorkAllocation.objects.all()
    for work in works:
        if work.status == 'Pending':
            work.status = 'workdesk'
            work.save()
            TechWorkList.objects.create(technician=request.user, work=work)

    # Get the current date or use the month and year from query parameters
    query_month = request.GET.get('month')
    query_year = request.GET.get('year')

    if query_month and query_year:
        selected_month = int(query_month)
        selected_year = int(query_year)
    else:
        today = now()
        selected_month = today.month
        selected_year = today.year

    # Get the start and end dates for the selected month
    from django.utils.timezone import make_aware

    print('selected month: ', selected_month)
    print('selected year',selected_year)
    # Make the start and end dates timezone-aware
    first_day_of_month = make_aware(datetime(selected_year, selected_month, 1))
    last_day_of_month = make_aware(datetime(selected_year, selected_month, monthrange(selected_year, selected_month)[1], 23, 59, 59))

    print("first day",first_day_of_month)
    print('last day of month', last_day_of_month)


    # Filter works for the selected month
    print('Filter Range:', first_day_of_month, '-', last_day_of_month)

    completed_works = TechWorkList.objects.filter(
        technician=user,
        status='Completed',
        completion_datetime__range=[first_day_of_month, last_day_of_month]
    )

    print('Completed Works:', completed_works)

    # Group works by week
    weekly_work_counts = {}
    current_date = first_day_of_month
    while current_date <= last_day_of_month:
        week_start = current_date
        week_end = week_start + timedelta(days=6)

        week_label = f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}"
        count = completed_works.filter(
            completion_datetime__range=[week_start, min(week_end, last_day_of_month)]
        ).count()

        weekly_work_counts[week_label] = count
        print(f"Week: {week_label}, Count: {count}")  # Debugging output
        current_date = week_end + timedelta(days=1)

    # Prepare data for the chart
    labels = list(weekly_work_counts.keys())
    data = list(weekly_work_counts.values())


    chart_data = {
        'labels': labels,
        'data': data
    }
    chart_data_json = json.dumps(chart_data)

    # Determine previous and next months for navigation
    previous_month = first_day_of_month - timedelta(days=1)
    next_month = last_day_of_month + timedelta(days=1)
    
    context = {
        'user': user,
        'technician_profile': technician_profile,
        'chart_data_json': chart_data_json,  # Pass chart data to the template
        'selected_month': selected_month,
        'selected_year': selected_year,
        'previous_month': previous_month,
        'next_month': next_month,
    }


    return render(request, 'technician_dashboard.html', context)

def create_superadmin(request):
    # List of superadmin details
    superadmins = [
        {
            'username': 'admin1',
            'email': 'superadmin1@example.com',
            'password': 'admin1'
        },
        {
            'username': 'admin2',
            'email': 'superadmin2@example.com',
            'password': 'admin2'
        }
    ]
    
    for admin in superadmins:
        # Check if the superadmin already exists
        if not User.objects.filter(username=admin['username']).exists():
            # Create a superuser with hardcoded values
            User.objects.create_superuser(
                username=admin['username'],
                email=admin['email'],
                password=admin['password']
            )
    
    return HttpResponse('Superadmins created successfully.')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import TechnicianProfile, WorkAllocation, service_management
# from .models import service_management, TechnicianProfile, WorkAllocation, TechWorkList
@login_required
def allocate_work(request, service_id):
    service_object = get_object_or_404(service_management, id=service_id)

    customer_fullname = service_object.customer.fullname
    customer_address = service_object.address
    customer_city = service_object.city
    customer_state = service_object.state
    customer_pincode = service_object.pincode
    customer_contact = service_object.customer.primarycontact
    payment_amount = service_object.total_price_with_gst
    gps_location = service_object.gps_location
    
    customer_address = f"{customer_address}, {customer_city}, {customer_state} - {customer_pincode}"

    
    if request.method == 'POST':
        technician_ids = request.POST.getlist('technicians')
        customer_address = request.POST.get('customer_address')
        work_description = request.POST.get('work_description')
        customer_payment_status = request.POST.get('customer_payment_status')

        # Create the work allocation
        work_allocation = WorkAllocation.objects.create(
            service=service_object,
            fullname=customer_fullname,
            customer_contact=customer_contact,
            customer_address=customer_address,
            work_description=work_description,
            customer_payment_status=customer_payment_status,
            payment_amount=payment_amount,
            gps_location=gps_location,
        )

        # Add all technicians to the WorkAllocation
        technicians = TechnicianProfile.objects.filter(id__in=technician_ids)
        work_allocation.technician.set(technicians)

        # Create TechWorkList for each technician
        for tech in technicians:
            tech_worklist = TechWorkList.objects.create(
                technician=tech.user,  
                service=service_object,
            )
            tech_worklist.work.add(work_allocation)

        return redirect('work_allocation_success')

    technicians = TechnicianProfile.objects.all()
    context = {
        'technicians': technicians,
        'customer_fullname': customer_fullname,
        'customer_address' : customer_address,
        'customer_contact': customer_contact,
        'payment_amount': payment_amount,
        'gps_location': gps_location,
    }
    return render(request, 'allocate_work.html', context)





from crmapp.models import Reschedule, service_management

def reschedule_create(request, service_id):
    service = get_object_or_404(service_management, id=service_id)
    if request.method == "POST":
        # Retrieve data from POST request
        reason = request.POST.get('reason', '').strip()
        if not reason:
            return render(request, 'reschedule_reason.html', {
                'error': 'Please provide a reason for rescheduling.',
                'service': service
            })

        # Log the reason in RescheduleLog
        Reschedule.objects.create(
            service=service,
            old_service_date=service.service_date,
            old_delivery_time=service.delivery_time,
            reason=reason
        )

        # Redirect to the edit form
        return redirect('edit_service_management', rid=service.id)

    return render(request, 'reschedule.html', {'service': service})


from django.core.paginator import Paginator

def technician_work_list(request):
    if not request.user.is_staff:
        return HttpResponse("Not authorized", status=403)

    # Fetch work allocations
    work_allocations = WorkAllocation.objects.all()

    # Set up pagination (10 items per page)
    paginator = Paginator(work_allocations, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'technician_work_list.html', {'page_obj': page_obj})



def edit_work(request, work_id):
    work_allocation = get_object_or_404(WorkAllocation, id=work_id)
    
    if request.method == 'POST':
        work_allocation.customer_name = request.POST.get('customer_name')
        work_allocation.work_description = request.POST.get('work_description')
        work_allocation.customer_payment_status = request.POST.get('customer_payment_status')
        work_allocation.payment_amount = request.POST.get('payment_amount')
        work_allocation.save()
        return redirect('technician_work_list')
    
    return render(request, 'edit_work.html', {'work_allocation': work_allocation})

def delete_work(request, work_id):
    if request.method == 'POST':
        work_allocation = get_object_or_404(WorkAllocation, id=work_id)
        work_allocation.delete()
        return redirect('technician_work_list')
    return HttpResponse("Method not allowed", status=405)




@login_required
def handle_work_allocation(request, work_id):
    work_allocation = get_object_or_404(WorkAllocation, id=work_id)
    
    if request.method == 'POST':
        status = request.POST.get('status')
        if status in ['Accepted', 'Rejected']:
            work_allocation.status = status
            work_allocation.save()
        return redirect('technician_work_list')
    
    return render(request, 'handle_work_allocation.html', {'work_allocation': work_allocation})

def work_allocation_success(request):
    return render(request, 'work_allocation_success.html')

@login_required
def pending_work(request):
    try:
        technician_profile = TechnicianProfile.objects.get(user=request.user)
    except TechnicianProfile.DoesNotExist:
        technician_profile = None

    pending_works = WorkAllocation.objects.filter(technician=technician_profile, status='Pending')

    # work_allocations = TechWorkList.objects.filter(technician=request.user)
    return render(request, 'pending_work.html', {'pending_works': pending_works })

    # return render(request, 'pending_work.html', {'pending_works': pending_works})


# views.py
# from django.shortcuts import redirect, render
# from paypalrestsdk import Payment
# from django.conf import settings
# import paypalrestsdk

# # Import the PayPal SDK configuration
# from .paypal import paypalrestsdk

# def create_paypal_payment(request):
#     if request.method == 'POST':
#         # Example payment details
#         payment = paypalrestsdk.Payment({
#             "intent": "sale",
#             "payer": {
#                 "payment_method": "paypal"
#             },
#             "redirect_urls": {
#                 "return_url": "http://localhost:8000/payment-success",
#                 "cancel_url": "http://localhost:8000/payment-cancel"
#             },
#             "transactions": [{
#                 "item_list": {
#                     "items": [{
#                         "name": "Quotation Payment",
#                         "sku": "12345",
#                         "price": "10.00",
#                         "currency": "USD",
#                         "quantity": 1
#                     }]
#                 },
#                 "amount": {
#                     "total": "10.00",
#                     "currency": "USD"
#                 },
#                 "description": "Payment for quotation."
#             }]
#         })

#         # Create the payment
#         if payment.create():
#             for link in payment.links:
#                 if link.rel == "approval_url":
#                     # Redirect the user to PayPal for authorization
#                     return redirect(link.href)
#         else:
#             print(payment.error)

#     return render(request, 'checkout.html')

# views.py
from django.shortcuts import redirect, render
from paypalrestsdk import Payment
from django.conf import settings
import paypalrestsdk

# Import the PayPal SDK configuration
from .paypal import paypalrestsdk

def create_paypal_payment(request):
    if request.method == 'POST':
        # Extracting invoice details from POST data or database
        customer_id = request.POST.get('customer_id')  # Assuming this is sent via POST
        total_amount_with_gst = request.POST.get('total_amount_with_gst')  # Total amount with GST
        company_name = request.POST.get('company_name')  # Assuming other params are also passed

        # Ensure that `total_amount_with_gst` is properly formatted
        total_amount_with_gst = format(float(total_amount_with_gst), '.2f')

        # Example payment details with dynamic data
        payment = paypalrestsdk.Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": "http://localhost:8000/payment-success",
                "cancel_url": "http://localhost:8000/payment-cancel"
            },
            "transactions": [{
                "item_list": {
                    "items": [{
                        "name": f"Invoice Payment for {company_name}",
                        "sku": customer_id,  # Using Customer ID as SKU
                        "price": total_amount_with_gst,  # Price in INR
                        "currency": "USD",  # Currency set to INR
                        "quantity": 1
                    }]
                },
                "amount": {
                    "total": total_amount_with_gst,  # Total amount from invoice
                    "currency": "USD"  # Set currency to INR
                },
                "description": f"Payment for Invoice from {company_name}."
            }]
        })

        # Create the payment
        if payment.create():
            for link in payment.links:
                if link.rel == "approval_url":
                    # Redirect the user to PayPal for authorization
                    return redirect(link.href)
        else:
            print(payment.error)

    return render(request, 'checkout.html')



# views.py
def payment_success(request):
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')

    payment = paypalrestsdk.Payment.find(payment_id)

    if payment.execute({"payer_id": payer_id}):
        # Payment was successful
        return render(request, 'payment_success.html')
    else:
        # Payment failed
        return render(request, 'payment_error.html')


def payment_cancel(request):
    # Handle cancellation
    return render(request, 'payment_cancel.html')


from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import WorkAllocation, TechWorkList
from django.contrib.auth.decorators import login_required

# @login_required
# def work_list(request):
    

# @login_required
# def accept_work(request, work_id):
#     work = get_object_or_404(WorkAllocation, id=work_id)
#     if request.method == 'POST':
#         work.status = 'Accepted'
#         work.save()
#         TechWorkList.objects.create(technician=request.user, work=work)
#         return redirect('work_list')
#     return render(request, 'accept_work.html', {'work': work})

# @login_required
# def reject_work(request, work_id):
#     work = get_object_or_404(WorkAllocation, id=work_id)
#     if request.method == 'POST':
#         work.status = 'Rejected'
#         work.save()
#         return redirect('pending_work')
#     return render(request, 'reject_work.html', {'work': work})

# @login_required
# def complete_work(request, work_id):
#     tech_work = get_object_or_404(TechWorkList, work_id=work_id, technician=request.user)
#     if request.method == 'POST':
#         if request.FILES.get('photo_before_service'):
#             tech_work.photo_before_service = request.FILES['photo_before_service']
#         if request.FILES.get('photo_after_service'):
#             tech_work.photo_after_service = request.FILES['photo_after_service']
#         if request.FILES.get('customer_signature_photo'):
#             tech_work.customer_signature_photo = request.FILES['customer_signature_photo']
#         if request.FILES.get('payment_photo'):
#             tech_work.payment_photo = request.FILES['payment_photo']

#         # Update payment status only if it's currently pending
#         if tech_work.work.customer_payment_status == 'Pending' and request.POST.get('customer_payment_status'):
#             tech_work.work.customer_payment_status = request.POST['customer_payment_status']

#         # Update work and tech work status
#         tech_work.status = 'Completed'
#         tech_work.work.status = 'Completed'
#         tech_work.work.save()
#         tech_work.save()
#         return redirect('completed_work_list')

#     return render(request, 'complete_work.html', {'tech_work': tech_work})

import base64
from django.core.files.base import ContentFile
from django.utils.timezone import now
from .models import TechWorkList, UploadedFile

@login_required
def complete_work(request, work_id):
    tech_work = get_object_or_404(TechWorkList, id=work_id, technician=request.user)
    print('techn_work',tech_work)
    
    if request.method == 'POST':
        # Get related work object (WorkAllocation)
        work_allocation = tech_work.work.first()  # Assuming only 1 work per tech_work

        # Handle Photos Before Service
        photos_before_service = request.FILES.getlist('photos_before_service')
        for photo in photos_before_service:
            uploaded_file = UploadedFile.objects.create(file=photo)
            tech_work.photos_before_service.add(uploaded_file)

        # Handle Photos After Service
        photos_after_service = request.FILES.getlist('photos_after_service')
        for photo in photos_after_service:
            uploaded_file = UploadedFile.objects.create(file=photo)
            tech_work.photos_after_service.add(uploaded_file)

        # Handle digital signature
        signature_data = request.POST.get('signature_data')
        if signature_data:
            format, imgstr = signature_data.split(';base64,')
            ext = format.split('/')[-1]
            signature_file = ContentFile(base64.b64decode(imgstr), name=f'xsignature.{ext}')
            tech_work.customer_signature_photo.save(f'signature_{work_allocation.id}.{ext}', signature_file)

        # Handle signature upload
        customer_signature_photo = request.FILES.get('customer_signature_photo')
        if customer_signature_photo:
            tech_work.customer_signature_photo = customer_signature_photo

        # Handle Payment Photos
        payment_photos = request.FILES.getlist('payment_photos')
        for photo in payment_photos:
            uploaded_file = UploadedFile.objects.create(file=photo)
            tech_work.payment_photos.add(uploaded_file)

        # Update customer payment status on WorkAllocation
        payment_status = request.POST.get('customer_payment_status')
        if payment_status in ['Pending', 'Online', 'Cash']:
            work_allocation.customer_payment_status = payment_status
            work_allocation.save()

        # Update all related TechWorkList entries for this work allocation
        related_tech_works = TechWorkList.objects.filter(work=work_allocation)
        for tw in related_tech_works:
            tw.status = 'Completed'
            tw.completion_datetime = now()
            tw.save()

        # Finally, mark the WorkAllocation as Completed
        work_allocation.status = 'Completed'
        work_allocation.save()

        return redirect('completed_work_list')
    return render(request, 'complete_work.html', {'tech_work': tech_work})


@login_required
def completed_work_list(request):
    completed_works = TechWorkList.objects.filter(technician=request.user, status='Completed')
    return render(request, 'completed_work_list.html', {'completed_works': completed_works})
@login_required
def work_details(request, work_id):
    work = get_object_or_404(TechWorkList, id=work_id, technician=request.user)
    
    related_technicians = []
    for wa in work.work.all():  # Assuming this is a ManyToMany of WorkAllocation objects
        for tech in wa.technician.all():  # Assuming ManyToMany of TechnicianProfile
            if tech.user != request.user:
                related_technicians.append(tech)
    
    # Remove duplicates if any
    related_technicians = list({tech.id: tech for tech in related_technicians}.values())
    
    return render(request, 'work_details.html', {
        'work': work,
        'related_technicians': related_technicians,
    })



def view_work_details(request, work_id):
    tech_work = get_object_or_404(TechWorkList, pk=work_id)
    context = {
        'tech_work': tech_work
    }
    return render(request, 'work_details.html', context)

# views.py

from django.shortcuts import render
from django.views.generic import ListView, DetailView
from .models import TechWorkList

class AdminCompletedWorkView(ListView):
    model = TechWorkList
    template_name = 'admin_completed_work_list.html'  
    context_object_name = 'completed_work_list'
    
    def get_queryset(self):
        return TechWorkList.objects.filter(status='Completed').exclude(customer_signature_photo='')

class AdminWorkDetailView(DetailView):
    model = TechWorkList
    template_name = 'admin_work_detail.html'
    context_object_name = 'work'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        work_instance = self.get_object()
        
        # Get all related technicians
        technicians_set = set()
        for wa in work_instance.work.all():
            for tech in wa.technician.all():
                technicians_set.add(tech)
        context['related_technicians'] = technicians_set

        # Get customer details from the first related WorkAllocation's service
        first_wa = work_instance.work.first()
        if first_wa and first_wa.service and first_wa.service.customer:
            customer = first_wa.service.customer
            context['customer'] = customer
        else:
            context['customer'] = None

        return context


def import_leads(request):
    if request.method == 'POST':
        form = LeadImportForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            file_type = file.name.split('.')[-1]
            if file_type == 'csv':
                handle_csv(file)
            elif file_type == 'xlsx':
                handle_xlsx(file)
            else:
                messages.error(request, 'Unsupported file format. Please upload a CSV or XLSX file.')
                return redirect('import_leads')
            
            return redirect('display_lead_management')  
    else:
        form = LeadImportForm()
    
    return render(request, 'import_leads.html', {'form': form})

def handle_csv(file):
    decoded_file = file.read().decode('utf-8').splitlines()
    reader = csv.reader(decoded_file)
    next(reader)  # Skip header row

    for row in reader:
        try:

            # dateoflead = datetime.strptime(row[6], '%Y-%m-%d').date()

            lead_management.objects.create(
                sourceoflead=row[0],
                salesperson=row[1],
                primarycontact=row[2],
                customeraddress=row[3],
                customeremail=row[4],
                enquirydate=row[5],
                typeoflead=row[6],
                city=row[7],
                contactedby=row[8],
                customername =row[9],
                customersegment=row[10],
                location=row[11],
                maincategory=row[12],
                secondarycontact=row[13],
                subcategory=row[14],
                firstfollowupdate=row[15],
                stage=row[16],
        )
            
        except ValueError as e:
            # Handle any errors with date parsing or other fields
            messages.error(request, f'Error in row: {row}. {e}')
        

def handle_xlsx(file):
    wb = openpyxl.load_workbook(file)
    sheet = wb.active

    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=1):
        lead_management.objects.create(
            sourceoflead=row[0],
            salesperson=row[1],
            primarycontact=row[2],
            customeraddress=row[3],
            customeremail=row[4],
            enquirydate=row[5],
            typeoflead=row[6],
            city=row[7],
            contactedby=row[8],
            customername =row[9],
            customersegment=row[10],
            location=row[11],
            maincategory=row[12],
            secondarycontact=row[13],
            subcategory=row[14],
            firstfollowupdate=row[15],
            stage=row[16],
        )
# try1









def calendar_view(request):
    return render(request, 'dashboard/dashboard.html')

def meeting_data(request):
    # Fetch all meetings
    meetings = Meeting.objects.all()
    events = []
    for meeting in meetings:
        # Calculate end time as 1 hour after start time
        start_datetime = datetime.datetime.combine(meeting.meeting_date, meeting.meeting_time)
        end_datetime = start_datetime + datetime.timedelta(hours=1)
        print("stratdate", start_datetime)
        print("enddatetiem", end_datetime)
        events.append({
            'title': f"{meeting.meeting_agenda}",
            'start': start_datetime.isoformat(),
            'end': end_datetime.isoformat(),
            'description': f"Agenda: {meeting.meeting_agenda}, Participants: {meeting.participants}"
        })
    return JsonResponse(events, safe=False)

# crmapp/views.py

import matplotlib.pyplot as plt
from io import BytesIO
import base64
from django.shortcuts import render
from crmapp.models import Product  # Your Product model

# def dashboard_view(request):
#     # Fetch the count of products per category
#     pest_control_count = Product.objects.filter(category='Pest Control').count()
#     fumigation_count = Product.objects.filter(category='Fumigation').count()
#     product_sell_count = Product.objects.filter(category='Product Sell').count()

#     # Prepare data for the bar chart
#     categories = ['Pest Control', 'Fumigation', 'Product Sell']
#     counts = [pest_control_count, fumigation_count, product_sell_count]

#     # Create the bar chart using matplotlib
#     fig, ax = plt.subplots()
#     ax.bar(categories, counts, color=['#FF6384', '#36A2EB', '#FFCE56'])
#     ax.set_title('Number of Products per Category')
#     ax.set_xlabel('Product Category')
#     ax.set_ylabel('Number of Products')

#     # Save the figure to a BytesIO object to convert it into an image for the web
#     buffer = BytesIO()
#     plt.savefig(buffer, format='png')
#     buffer.seek(0)
    
#     # Convert the image to base64
#     image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

#     # Prepare context
#     context = {
#         'product_chart': image_base64,  # Send the chart as a base64 string to the template
#     }

#     return render(request, 'dashboard/dashboard.html', context)


@login_required
def go_towork(request, work_id):
    work = get_object_or_404(WorkAllocation, id=work_id)
    if request.method == 'POST':
        work.status = 'workdesk'
        work.save()
        TechWorkList.objects.create(technician=request.user, work=work)
        return redirect('work_list')
    return render(request, 'accept_work.html', {'work': work})

from django.shortcuts import render
from .models import WorkAllocation  # Import your model here

@login_required
def work_list_view(request):
    # Get search query
    query = request.GET.get('search', '')

    # Base queryset: only Pending work for this technician
    work_allocations = TechWorkList.objects.filter(
        technician=request.user,
        status="Pending"
    )

    # Apply search filter if query is provided
    if query:
        work_allocations = work_allocations.filter(
            Q(work__customer_contact__icontains=query)
        )

    # Debug (Optional)
    for work in work_allocations:
        print("work:", work, "| status:", work.status)

    return render(request, 'work_list.html', {'work_allocations': work_allocations})

from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from crmapp.models import TechWorkList
from django.templatetags.static import static

def view_work_pdf(request, work_id):
    work = get_object_or_404(TechWorkList, pk=work_id, technician=request.user)
    logo_path = request.build_absolute_uri(static('images/Logo.png'))

    context = {'work': work,'logo_path': logo_path}
    html = render_to_string('work_pdf_template.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="work_{work_id}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating the PDF', status=400)
    
    return response

def download_work_pdf(request, work_id):
    work = get_object_or_404(TechWorkList, pk=work_id, technician=request.user)
    logo_path = request.build_absolute_uri(static('images/logo.png'))

    context = {'work': work,'logo_path': logo_path}
    html = render_to_string('work_pdf_template.html', context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="work_{work_id}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating the PDF', status=400)
    
    return response


from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
import urllib.parse

def generate_pdf_link(request, work_id):
    work = get_object_or_404(TechWorkList, id=work_id)
    pdf_url = request.build_absolute_uri(reverse('download_work_pdf', args=[work_id]))
    whatsapp_message = f"Here is your service report: {pdf_url}"
    encoded_message = urllib.parse.quote(whatsapp_message)
    whatsapp_url = f"https://wa.me/{work.work.customer_contact}?text={encoded_message}"
    return redirect(whatsapp_url)




from django.shortcuts import render, redirect
from .models import Branch

from .models import Branch

def create_branch(request):
    if request.method == 'POST':
        branch_name = request.POST.get('branch_name')
        contact_1 = request.POST.get('contact_1')
        contact_2 = request.POST.get('contact_2') or None
        email_1 = request.POST.get('email_1')
        email_2 = request.POST.get('email_2') or None
        gst_number = request.POST.get('gst_number')
        pan_number = request.POST.get('pan_number')
        state = request.POST.get('state')
        code = request.POST.get('code')
        shortcut = request.POST.get('shortcut')
        full_address = request.POST.get('full_address')

        # Only pass state; model will set shortcut and code
        branch = Branch(
            branch_name=branch_name,
            contact_1=contact_1,
            contact_2=contact_2,
            email_1=email_1,
            email_2=email_2,
            gst_number=gst_number,
            pan_number=pan_number,
            state=state,
            code = code,
            shortcut = shortcut,
            full_address=full_address
        )
        branch.save()  
        return redirect('branch_list')
   
    return render(request, 'create_branch.html' , {"state_map":state_map})


def branch_list(request):
    branches = Branch.objects.all().order_by('-created_at')
    return render(request, 'branch_list.html', {'branches': branches})


def get_branch_details(request, branch_id):
    try:
        branch = Branch.objects.get(id=branch_id)
        data = {
            'contact_1': branch.contact_1,
            'contact_2': branch.contact_2 or '',
            'email_1': branch.email_1,
            'email_2': branch.email_2 or '',
            'gst_number': branch.gst_number,
            'pan_number': branch.pan_number,
            'full_address': branch.full_address,
            'state': branch.state,
            'code': branch.code,
            'shortcut': branch.shortcut,
        }
        return JsonResponse(data)
    except Branch.DoesNotExist:
        return JsonResponse({'error': 'Branch not found'}, status=404)    


def get_customer_details(request):
    if 'contact_no' in request.GET:
        contact_no = request.GET.get('contact_no')
        try:
            customer = customer_details.objects.get(primarycontact=contact_no)
            data = {
                'customer_full_name': customer.fullname,
                'customer_email': customer.primaryemail,
                'soldtopartyaddress': customer.soldtopartyaddress,
                'city': customer.soldtopartycity,
                'state': customer.soldtopartystate,
                'pincode':customer.soldtopartypostal
            }
            return JsonResponse(data)
        except customer_details.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=404)
    return JsonResponse({'error': 'No contact number provided'}, status=400)



from .models import BankAccounts   
from django.http import JsonResponse

from .models import BankAccounts  # Make sure the model is correctly imported
from django.views.decorators.http import require_POST

@login_required
def create_bank_account(request):
    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        account_number = request.POST.get('bank_account_number')
        ifs_code = request.POST.get('ifs_code')
        branch = request.POST.get('branch')


        if not all([bank_name, account_number, ifs_code, branch]):
            return JsonResponse({'error': 'All fields are required'}, status=400)
        
     
        if BankAccounts.objects.filter(account_number=account_number).exists():
            return JsonResponse({'error': 'Bank account already exists'}, status=409)

        BankAccounts.objects.create(
            bank_name=bank_name,
            account_number=account_number,
            ifs_code=ifs_code,
            branch=branch
        )
        return redirect('list_bank_accounts') 

    return render(request, 'create_bank_account.html')

@login_required
def list_bank_accounts(request):
    accounts = BankAccounts.objects.all()
    return render(request, 'list_bank_accounts.html', {'bank_accounts': accounts})

@login_required
def edit_bank_account(request, account_id):
    bank_account = get_object_or_404(BankAccounts, id=account_id)

    if request.method == 'POST':
        bank_name = request.POST.get('bank_name')
        account_number = request.POST.get('bank_account_number')
        ifs_code = request.POST.get('ifs_code')
        branch = request.POST.get('branch')

        if not all([bank_name, account_number, ifs_code, branch]):
            return render(request, 'edit_bank_account.html', {
                'error': 'All fields are required',
                'bank': bank_account
            })

        # Optional: Check if another account exists with the same number
        if BankAccounts.objects.filter(account_number=account_number).exclude(id=bank_account.id).exists():
            return render(request, 'edit_bank_account.html', {
                'error': 'Another account with this number already exists',
                'bank': bank_account
            })

        # Update fields
        bank_account.bank_name = bank_name
        bank_account.account_number = account_number
        bank_account.ifs_code = ifs_code
        bank_account.branch = branch
        bank_account.save()

        return redirect('list_bank_accounts')

    return render(request, 'edit_bank_account.html', {'bank': bank_account})


@login_required
@require_POST
def delete_bank_account(request, account_id):
    bank_account = get_object_or_404(BankAccounts, id=account_id)
    bank_account.delete()
    return redirect('list_bank_accounts')


# def create_tax_invoice(request):
#     if request.method == "POST":
#         quotation_no = request.POST.get("quotation_no")
#         hsn_sac = request.POST.get("hsn_sac")

#         reference = request.POST.get("referance_no_and_date")
#         bank_id = request.POST.get("bank_id")  

#         # Fetch quotation
#         quotation = quotation_management.objects.filter(quotation_number=quotation_no).first()

#         if not quotation:
#             messages.error(request, "Quotation number not found.")
#             return render(request, "create_tax_invoice.html")

#         # Get related customer and bank
#         customer = getattr(quotation, 'customer', None)
#         if not customer:
#             messages.error(request, "Customer not found for this quotation.")
#             return render(request, "create_tax_invoice.html")

#         bank = get_object_or_404(BankAccounts, id=bank_id)

#         # Check for existing invoice
#         if TaxInvoice.objects.filter(quotation=quotation).exists():
#             messages.warning(request, "Invoice already created for this quotation.")
#             return render(request, "create_tax_invoice.html")

#         # Create invoice – tax_invoice_no will be auto-generated
#         invoice = TaxInvoice.objects.create(
#             quotation=quotation,
#             customer=customer,
#             bank=bank,
#             hsn_sac=hsn_sac,
#             referance_no_and_date=reference
#         )

#         messages.success(request, f"Tax Invoice Created: {invoice.tax_invoice_no}")
#         return redirect("create_tax_invoice")  # or redirect to invoice detail

#     context = {
#     'customers': customer_details.objects.all(),
#     'banks': BankAccounts.objects.all()
#     }
#     return render(request, "create_tax_invoice.html", context=context)


from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from .models import TaxInvoice, TaxInvoiceItem, quotation_management, customer_details, BankAccounts
import json
from datetime import datetime
from weasyprint import HTML

def create_tax_invoice(request):
    if request.method == "POST":
        try:
            # 1. Get quotation and related data
            quotation_no = request.POST.get("quotation_no")
            quotation = get_object_or_404(quotation_management, quotation_no=quotation_no)
            customer = get_object_or_404(customer_details, primarycontact=quotation.contact_no)
            bank_id = request.POST.get("bank_id")
            bank = get_object_or_404(BankAccounts, id=bank_id)

            # 2. Get product data
            product_data = request.POST.get("product_data", "[]")
            items = json.loads(product_data)
            # 4. Create TaxInvoice with grand_total
            invoice = TaxInvoice.objects.create(
                quotation=quotation,
                customer=customer,
                bank=bank,
                referance_no_and_date=request.POST.get("referance_no_and_date"),
                other_referance=request.POST.get("other_references"),
                delivery_note=request.POST.get("delivery_note"),
                modern_terms_of_payment=request.POST.get("mode_terms_of_payment"),
                buyers_order_no=request.POST.get("buyer_order_no"),
                dated=parse_date_or_none(request.POST.get("dated")),
                dispatch_doc_no=request.POST.get("dispatch_doc_no"),
                delivery_note_date=parse_date_or_none(request.POST.get("delivery_note_date")),
                dispatched_through=request.POST.get("dispatched_through"),
                destination=request.POST.get("destination"),
                service_titel=request.POST.get('service_titel'),
                shift_gstin_uin=request.POST.get('shift_gstin_uin'),
                shifttopartystate=request.POST.get('shifttopartystate'),
                shifttopartystatecode=request.POST.get('shifttopartystatecode'),
                sold_gstin_uin=request.POST.get('sold_gstin_uin'),
                soldtopartystate=request.POST.get('soldtopartystate'),
                soldtopartystatecode=request.POST.get('soldtopartystatecode'),
                # grand_total=grand_total  # ✅ Use the calculated value here
            )

            # 5. Save products       
            grand_total = 0
            for item in items:
                price = float(item.get('price', 0))
                quantity = float(item.get('quantity', 0))
                print("q",quantity)
                gst_percent = float(item.get('gst', 0))
                gst_amount = round((price * quantity * gst_percent) / 100,2)
                print("gst",gst_amount)
                total = price * quantity 
                grand_total += total + gst_amount

                TaxInvoiceItem.objects.create(
                    tax_invoice=invoice,
                    product_name=item.get('name'),
                    hsn_code=item.get('hsn'),
                    quantity=quantity,
                    unit=item.get('unit'),
                    price=price,
                    gst_percent=gst_percent,
                    gst_amount=gst_amount,
                    total=total
                )
            
            invoice.grand_total = grand_total
            invoice.save()



            return redirect("tax_invoice_pdf")

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    banks = BankAccounts.objects.all()
    return render(request, "create_tax_invoice.html", {'banks': banks})

def parse_date_or_none(date_str):
    """Utility to parse date from string or return None."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
    except:
        return None



def display_tax_invoice(request):
    query = request.GET.get('search', '')
    sort_by = request.GET.get('sort_by', '')
    sort_order = request.GET.get('order', 'asc')
    
    
    if query:
        m = TaxInvoice.objects.filter(
            Q(customer__customerid__icontains=query) |
            Q(tax_invoice_no__icontains=query)
        )
    else:
        m = TaxInvoice.objects.all().prefetch_related('items')

    
    if sort_by == 'firstname':
        sort_field = 'customer__fullname'
    elif sort_by == 'invoice_no':
        sort_field = 'tax_invoice_no'
    else:
        sort_field = 'id'  # default sorting if no valid sort_by is provided

    # Apply ordering based on direction
    if sort_order == 'desc':
        m = m.order_by(f'-{sort_field}')
    else:
        m = m.order_by(sort_field)

    paginator = Paginator(m, 10)  
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    start_index = (page_obj.number - 1) * paginator.per_page

    context = {
        'current_order': sort_order,
        'current_sort_by': sort_by,
        'query': query,
        'page_obj': page_obj,
        'start_index': start_index,
    }
    return render(request, 'display_invoice.html', context)



def tax_invoice_pdf(request, id):
    invoice = get_object_or_404(TaxInvoice, id=id)
    items = invoice.items.all()
    cgst = invoice.quotation.cgst
    sgst = invoice.quotation.sgst
    igst = invoice.quotation.igst
    amount_in_words = price_in_words(invoice.grand_total)
    # print("data" ,invoice.quotation.igst )
    context = {
        'invoice': invoice,
        'items': items,
        'cgst_total': cgst,
        'sgst_total': sgst,
        'igst_total':igst,
        'amount_in_words':amount_in_words,
        'today': datetime.now(),
    }

    
    # Render the template
    template_path = 'tax_invoice_pdf.html'
    template = get_template(template_path)
    html_string = template.render(context)

    # Generate PDF
    html = HTML(string=html_string, base_url=request.build_absolute_uri())
    pdf = html.write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    # Check if 'download=true' is passed in query params
    if request.GET.get('download') == 'true':
        response['Content-Disposition'] = f'attachment; filename="TaxInvoice_{invoice.id}.pdf"'
    else:
        response['Content-Disposition'] = f'inline; filename="TaxInvoice_{invoice.id}.pdf"'


    return response

