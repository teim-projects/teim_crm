from django.utils import timezone
import requests
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Meeting
from crmapp.models import customer_details, SalesPerson, BranchManager



def schedule_meeting(request):
    return render(request , 'schedule_meetings/schedule_meetings.html')

@login_required
def meeting_list(request):
    customers = customer_details.objects.all()  # Fetch all customers from the database

    if request.method == 'POST':
        customer_id = request.POST['customer_id']
        customer = customer_details.objects.get(id=customer_id)
        meeting_date = request.POST['meeting_date']
        meeting_time = request.POST['meeting_time']
        participants = request.POST['participants']
        meeting_agenda = request.POST['meeting_agenda']
        minutes_of_meeting = request.POST['minutes_of_meeting']
        
        # Automatically fetch today's date
        # meeting_date = timezone.now().date()

        # Save the meeting details in the database
        meeting = Meeting(
            customer = customer,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            participants=participants,
            meeting_agenda=meeting_agenda,
            minutes_of_meeting=minutes_of_meeting
        )
        meeting.save()

        return redirect('/index')  # Redirect to a index
    
    else:
        today_date = timezone.now().date()  # Fetch today's date using Django's timezone

        context = {
            'customers': customers,
            'today_date': today_date  # Pass today's date to the template
        }
        return render(request, 'schedule_meetings/meeting_list.html', context)
    
# def display_meeting(request):
#     m=Meeting.objects.all()

#     context={}
#     context['data'] =m
#     return render(request , 'schedule_meetings/display_meeting.html' , context)

@login_required
def display_meeting(request):
    user_role = getattr(getattr(request.user, 'userprofile', None), 'role', '')
    is_admin = request.user.is_superuser or user_role in ['admin', 'HO_operation', 'HO_manager']

    if is_admin:
        m = Meeting.objects.all()
    elif user_role == 'branch_manager':
        bm = BranchManager.objects.filter(mobile_no=request.user.username).first()
        if bm:
            m = Meeting.objects.filter(customer__branch_id=bm.branch)
        else:
            m = Meeting.objects.none()
    elif user_role == 'sales':
        sp = SalesPerson.objects.filter(
            Q(mobile_no=request.user.username) | Q(email=request.user.email)
        ).first()
        if sp:
            m = Meeting.objects.filter(
                Q(customer__contactperson__iexact=sp.full_name) | Q(customer__primarycontact=sp.mobile_no)
            )
        else:
            m = Meeting.objects.none()
    else:
        m = Meeting.objects.none()

    # Check if the user has submitted a search query
    customer_id = request.GET.get('customer_id')
    meeting_date = request.GET.get('meeting_date')

    if customer_id:  # If searching by customer ID
        m = m.filter(customer__customerid__icontains=customer_id)

    if meeting_date:  # If searching by meeting date
        m = m.filter(meeting_date=meeting_date)  # Filter by date

    context = {
        'data': m,
        'customer_id': customer_id or '',
        'meeting_date': meeting_date or ''
    }
    
    return render(request, 'schedule_meetings/display_meeting.html', context)
