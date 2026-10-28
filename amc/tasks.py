from celery import shared_task
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta

from .models import AMCContract
from amc.models import AMCServiceSchedule, AMCServiceVisit



@shared_task
def check_expiring_amcs():
    today = timezone.now().date()
    print(f"[AMC TASK] Running expiry check for {today}")

    # Only active AMCs
    amcs = AMCContract.objects.filter(is_active=True)

    for amc in amcs:
        days_left = (amc.end_date - today).days

        print(
            f"[AMC TASK] {amc.contract_number} | "
            f"End: {amc.end_date} | Days left: {days_left}"
        )

        customer = amc.customer

        if not customer.primaryemail:
            print(f"[AMC TASK] No email for {amc.contract_number}")
            continue

        # 🔔 15 DAYS BEFORE EXPIRY — SEND ONCE (YES / NO LINKS)
        if days_left == 15 and not amc.reminder_15_days_sent:
            subject = f"AMC Expiry Reminder – {amc.contract_number}"

            yes_url = f"http://127.0.0.1:8000/amc/renew/yes/{amc.contract_number}/"
            no_url = f"http://127.0.0.1:8000/amc/renew/no/{amc.contract_number}/"

            message = f"""
Dear {customer.fullname},


Your AMC ({amc.contract_number}) will expire on {amc.end_date}.

Do you want to renew your AMC?

YES → {yes_url}
NO  → {no_url}

Our admin team will contact you after confirmation.

Thank you,
Support Team
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.primaryemail],
                fail_silently=False,
            )

            amc.reminder_15_days_sent = True
            amc.save(update_fields=["reminder_15_days_sent"])

            print(f"[AMC TASK] 15-day reminder sent for {amc.contract_number}")

        # 🔴 ON EXPIRY DAY — SEND ONCE
        if days_left == 0 and not amc.expiry_mail_sent:
            subject = f"AMC Expired – {amc.contract_number}"

            message = f"""
Dear {customer.fullname},


Your AMC ({amc.contract_number}) has expired on {amc.end_date}.

If you wish to renew, please contact our support team.

Thank you,
Support Team
"""

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [customer.primaryemail],
                fail_silently=False,
            )

            amc.expiry_mail_sent = True
            amc.save(update_fields=["expiry_mail_sent"])

            print(f"[AMC TASK] Expiry mail sent for {amc.contract_number}")

        # 🛑 AUTO-EXPIRE AMC (AFTER EXPIRY DATE)
        if days_left < 0 and amc.is_active:
            amc.status = "Expired"
            amc.is_active = False
            amc.save(update_fields=["status", "is_active"])

            print(f"[AMC TASK] AMC auto-expired: {amc.contract_number}")



@shared_task
def send_service_reminder_emails():
    """
    Send reminder email 1 day before AMC service date
    """

    today = timezone.now().date()
    tomorrow = today + timedelta(days=1)

    schedules = AMCServiceSchedule.objects.filter(
        service_date=tomorrow,
        reminder_sent=False,
        amc__is_active=True
    )

    for schedule in schedules:
        amc = schedule.amc
        customer = amc.customer

        if not customer.primaryemail:
            continue

        subject = f"AMC Service Reminder – {amc.contract_number}"

        message = f"""
Dear {customer.fullname},

This is a reminder that your AMC service is scheduled for tomorrow.

AMC Contract : {amc.contract_number}
Service Date : {schedule.service_date}

Thank you,
Support Team
"""

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [customer.primaryemail],
            fail_silently=False,
        )

        schedule.reminder_sent = True
        schedule.save(update_fields=["reminder_sent"])


@shared_task
def create_service_visit_on_service_day():
    """
    Auto-create AMCServiceVisit on service date
    """

    today = timezone.now().date()

    schedules = AMCServiceSchedule.objects.filter(
        service_date=today,
        is_completed=False,
        amc__is_active=True
    )

    for schedule in schedules:
        amc = schedule.amc

        # Prevent duplicate visits
        if AMCServiceVisit.objects.filter(
            amc=amc,
            service_date=today
        ).exists():
            continue

        visit = AMCServiceVisit.objects.create(
            amc=amc,
            service_date=today
        )

        schedule.is_completed = True
        schedule.save(update_fields=["is_completed"])


from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import AMCServiceVisit


from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.conf import settings

from .models import AMCServiceVisit


@shared_task
def auto_allocate_amc_work():

    today = timezone.now().date()
    target_date = today + timedelta(days=2)

    print("AUTO AMC ALLOCATION TASK RUNNING")
    print("Today:", today)
    print("Target Date:", target_date)

    visits = AMCServiceVisit.objects.filter(
        service_date=target_date,
        allocation_status="PENDING",
        auto_allocation_done=False
    )

    print("Visits found:", visits.count())

    for visit in visits:

        if not visit.technicians.exists():
            print("No technician assigned")
            continue

        visit.allocation_status = "ALLOCATED"
        visit.auto_allocation_done = True
        visit.save()

        print(f"Visit {visit.id} allocated")

        amc = visit.amc
        customer = amc.customer
        technicians = visit.technicians.all()
        sales_email = amc.service.sales_person_email
        sales_name = amc.service.sales_person_name
        gps = amc.default_gps_location

        tech_names = []
        tech_contacts = []

        for t in technicians:
            tech_names.append(f"{t.first_name} {t.last_name}")
            tech_contacts.append(t.contact_number)

        tech_names_str = ", ".join(tech_names)
        tech_contacts_str = ", ".join(tech_contacts)

        print("Customer email:", customer.primaryemail)

        # CUSTOMER EMAIL
        if customer.primaryemail:

            send_mail(
                "AMC Service Technician Assigned",
                f"""
Dear {customer.fullname},

Your AMC service has been scheduled.

AMC Contract: {amc.contract_number}
Service Date: {visit.service_date}

Technician Assigned:
{tech_names_str}

Technician Contact:
{tech_contacts_str}

Service Address:
{customer.shifttopartyaddress}

Location:
{gps}
""",
                settings.EMAIL_HOST_USER,
                [customer.primaryemail],
                fail_silently=False
            )

            print("Customer email sent")

        # TECHNICIAN EMAIL
        for tech in technicians:

            print("Technician email:", tech.email)

            if tech.email:
                send_mail(
                    "New AMC Work Assigned",
                    f"""
Hello {tech.first_name},

You have been assigned a new AMC service.

Customer: {customer.fullname}
Customer Contact: {customer.primarycontact}

Service Date: {visit.service_date}

Address:
{customer.shifttopartyaddress}

GPS Location:
{gps}
""",
                    settings.EMAIL_HOST_USER,
                    [tech.email],
                    fail_silently=False
                )

                print("Technician email sent")

        # SALES PERSON EMAIL
        # SALES PERSON EMAIL
        if sales_email:
        
            send_mail(
                "AMC Work Allocated",
                f"""
        Hello {sales_name},
        
        AMC service has been allocated.
        
        Customer: {customer.fullname}
        Service Date: {visit.service_date}
        AMC Contract: {amc.contract_number}
        
        Technicians:
        {tech_names_str}
        
        Location:
        {gps}
        """,
                settings.EMAIL_HOST_USER,
                [sales_email],
                fail_silently=False
            )
        
            print("Sales email sent")

    return "AMC allocation + notifications completed"