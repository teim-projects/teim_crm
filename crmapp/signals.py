# signals.py

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver, Signal
from django.db import transaction
from django.contrib.auth.models import User
from .models import UserProfile, TechWorkList, TechnicianProfile, service_management
from crmapp.tasks import send_service_email


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)



# # When TechWorkList is created → mark as notification
# @receiver(post_save, sender=TechWorkList)
# def mark_new_work_as_notification(sender, instance, created, **kwargs):
#     print("Signal is called.....")
#     if created:
#         instance.is_notified = True
#         instance.save()

@receiver(post_save, sender=TechWorkList)
def mark_new_work_as_notification(sender, instance, created, **kwargs):
    if created:
        # Mark as notified internally
        instance.is_notified = True
        instance.save(update_fields=['is_notified'])

@receiver(post_save, sender=service_management)
def notify_customer_on_service_update(sender, instance, created, **kwargs):
    if not created:  # only run on updates, not creation
        transaction.on_commit(
            lambda: service_scheduled.send(
                sender=service_management,
                service_id=instance.id
            )
        )


# Signal: triggered when customer should be notified
service_scheduled = Signal()

@receiver(service_scheduled)
def send_service_scheduled_email(sender, service_id, **kwargs):
    from .models import service_management  # import here to avoid circular imports

    service = service_management.objects.get(id=service_id)
    customer = getattr(service, "customer", None)
    
    if not customer or not customer.primaryemail:
        return

    # Pick first technician
    techwork = service.techworklist_set.order_by("id").first()
    if not techwork:
        return
    tech_user = techwork.technician

    try:
        profile = TechnicianProfile.objects.get(user=tech_user)
        tech_details = f"{profile.first_name} {profile.last_name} - {profile.contact_number}"
    except TechnicianProfile.DoesNotExist:
        tech_details = f"{tech_user.first_name} {tech_user.last_name}"

    subject = "Service Appointment Confirmation – Seva Facility Services"

    message = f"""
Dear {customer.fullname},

We are pleased to inform you that your service has been successfully scheduled.

📅 Date: {service.service_date}
⏰ Time: {service.delivery_time.strftime("%I:%M %p")}
🛠 Service: {service.selected_services}
👨‍🔧 Technician: {tech_details}

Our technician will reach your location as per the scheduled time.  
Please ensure that someone is available to assist during the visit.

Thank you for choosing Seva Facility Services Pvt Ltd.
We look forward to serving you.

Warm regards, 
Seva Facility Services Pvt Ltd.
sevasupport@gmail.com
1234567890
"""

    send_service_email.delay(subject, message, customer.primaryemail)
    print("📧 Email task queued for:", customer.primaryemail)



