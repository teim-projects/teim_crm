# signals.py

from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver, Signal
from django.db import transaction
from django.contrib.auth.models import User
from .models import UserProfile, TechWorkList, TechnicianProfile, service_management
from crmapp.tasks import send_email_task


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

# @receiver(post_save, sender=service_management)
# def notify_customer_on_service_update(sender, instance, created, **kwargs):
#     if not created:  # only run on updates, not creation
#         transaction.on_commit(
#             lambda: service_scheduled.send(
#                 sender=service_management,
#                 service_id=instance.id
#             )
#         )

# @receiver(post_save, sender=service_management)
# def notify_customer_on_service_save(sender, instance, created, **kwargs):
#     transaction.on_commit(
#         lambda: service_scheduled.send(
#             sender=service_management,
#             service_id=instance.id
#         )
#     )

@receiver(post_save, sender=service_management)
def notify_customer_on_service_save(sender, instance, created, **kwargs):
    """
    Send email notification to customer when a service is created or updated.
    Differentiates between creation and update.
    """
    # Use transaction.on_commit to ensure DB changes are saved
    transaction.on_commit(lambda: service_scheduled.send(
        sender=service_management,
        service_id=instance.id,
        created=created  # pass the created flag to the custom signal
    ))


# Signal: triggered when customer should be notified
service_scheduled = Signal()

# @receiver(service_scheduled)
# def send_service_scheduled_email(sender, service_id, **kwargs):
#     from .models import service_management, MessageTemplates  # import here to avoid circular imports

#     template = MessageTemplates.objects.filter(category="service").first()
#     if not template:
#         return 
#     service = service_management.objects.get(id=service_id)
#     customer = getattr(service, "customer", None)
    
#     if not customer or not customer.primaryemail:
#         return

#     # Pick first technician
#     techwork = service.techworklist_set.order_by("id").first()
#     if not techwork:
#         return
#     tech_user = techwork.technician

#     try:
#         profile = TechnicianProfile.objects.get(user=tech_user)
#         tech_details = f"{profile.first_name} {profile.last_name} - {profile.contact_number}"
#     except TechnicianProfile.DoesNotExist:
#         tech_details = f"{tech_user.first_name} {tech_user.last_name}"

#     # Mapping of placeholder keys to actual values
#     placeholders = {
#         "customer_name": customer.fullname,
#         "service_date": service.service_date.strftime("%d-%m-%Y"),
#         "delivery_time": service.delivery_time.strftime("%I:%M %p"),
#         "selected_services": service.service_subject,
#         "tech_details": tech_details,
#     }
#     subject = "Service Appointment Confirmation – Seva Facility Services"
#     body = template.body
#     for key, value in placeholders.items():
#         body = body.replace(f"{{{key}}}", str(value))
# #     message = f"""
# # Dear {customer.fullname},

# # We are pleased to inform you that your service has been successfully scheduled.

# # 📅 Date: {service.service_date}
# # ⏰ Time: {service.delivery_time.strftime("%I:%M %p")}
# # 🛠 Service: {service.selected_services}  
# # 👨‍🔧 Technician: {tech_details}

# # Our technician will reach your location as per the scheduled time.  
# # Please ensure that someone is available to assist during the visit.

# # Thank you for choosing Seva Facility Services Pvt Ltd.
# # We look forward to serving you.

# # Warm regards, 
# # Seva Facility Services Pvt Ltd.
# # sevasupport@gmail.com
# # 1234567890
# # """

#     send_service_email.delay(subject, body, customer.primaryemail)
#     print("📧 Email task queued for:", customer.primaryemail)
@receiver(service_scheduled)
def send_service_scheduled_email(sender, service_id, created, **kwargs):
    from .models import service_management, MessageTemplates

    service = service_management.objects.get(id=service_id)
    customer = getattr(service, "customer", None)
    if not customer or not customer.primaryemail:
        return

    template = MessageTemplates.objects.filter(category="service").first()
    if not template:
        return

    # Pick first technician
    techwork = service.techworklist_set.order_by("id").first()
    if techwork:
        tech_user = techwork.technician
        try:
            profile = TechnicianProfile.objects.get(user=tech_user)
            tech_details = f"{profile.first_name} {profile.last_name} - {profile.contact_number}"
        except TechnicianProfile.DoesNotExist:
            tech_details = f"{tech_user.first_name} {tech_user.last_name}"
    else:
        tech_details = "Not Assigned"

    # Mapping placeholders
    placeholders = {
        "customer_name": customer.fullname,
        "service_date": service.service_date.strftime("%d-%m-%Y"),
        "delivery_time": service.delivery_time.strftime("%I:%M %p"),
        "selected_services": service.service_subject,
        "tech_details": tech_details,
    }

    body = template.body
    for key, value in placeholders.items():
        body = body.replace(f"{{{key}}}", str(value))

    # Subject can differ for creation vs update
    subject = "Service Appointment Confirmation – Seva Facility Services"
    if not created:
        subject = "Service Appointment Updated – Seva Facility Services"

    send_email_task.delay(subject, body, recipient_list = customer.primaryemail)
    print("📧 Email task queued for:", customer.primaryemail)



