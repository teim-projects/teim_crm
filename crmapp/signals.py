# signals.py
import requests
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver, Signal
from django.db import transaction
from django.contrib.auth.models import User
from .models import UserProfile, TechWorkList, TechnicianProfile, service_management,WorkAllocation
from crmapp.tasks import send_email_task,send_whatsapp_task


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)




@receiver(post_save, sender=TechWorkList)
def mark_new_work_as_notification(sender, instance, created, **kwargs):
    # print('mark_new_work_as_notification')
    if created:
        # Mark as notified internally
        instance.is_notified = True
        instance.save(update_fields=['is_notified'])



# @receiver(post_save, sender=service_management)
# def notify_customer_on_service_save(sender, instance, created, **kwargs):
#     """
#     Send email notification to customer when a service is created or updated.
#     Differentiates between creation and update.
#     """
#     # print('notify_customer_on_service_save')
#     # Use transaction.on_commit to ensure DB changes are saved
#     if not instance.customer_id:  # skip if no customer yet
#         return
#     transaction.on_commit(lambda: service_scheduled.send(
#         sender=service_management,
#         service_id=instance.id,
#         created=created  # pass the created flag to the custom signal
#     ))

# @receiver(post_save, sender=service_management)
# def notify_customer_on_service_update(sender, instance, created, **kwargs):
#     """
#     Trigger notification only when a service is created.
#     """
#     if not created:
#         return  # skip updates
#     if not instance.customer_id:
#         return

#     transaction.on_commit(lambda: service_scheduled.send(
#         sender=service_management,
#         service_id=instance.id,
#         created=True  # service created
#     ))


@receiver(post_save, sender=WorkAllocation)
def notify_customer_on_workallocation(sender, instance, created, **kwargs):
    """
    Trigger notification only when a work allocation is created.
    """

    print("signall is called..........")
    # if not created:
    #     return  # skip updates

    service = instance.service
    print("service_id",service.id)
    if not service or not service.customer_id:
        return

    transaction.on_commit(lambda: service_scheduled.send(
        sender=WorkAllocation,
        service_id=service.id,
        created=created    
    ))

# Signal: triggered when customer should be notified
service_scheduled = Signal()




@receiver(service_scheduled)
def send_service_scheduled_email(sender, service_id, created, **kwargs):
    from .models import service_management, MessageTemplates,WorkAllocation
    service = service_management.objects.get(id=service_id)
    customer = getattr(service, "customer", None)

    if not customer:
        return

    # ---------------- Email ----------------
    if customer.primaryemail:
        email_template = MessageTemplates.objects.filter(
            message_type="email", category="service"
        ).first()
        if email_template:
            # Pick first technician
           # Pick first technician from WorkAllocation
            work = WorkAllocation.objects.filter(service=service_id).first()
            if work and work.technician.exists():
                tech_profile = work.technician.first()  # ManyToMany
                tech_details = f"{tech_profile.first_name} {tech_profile.last_name} - {tech_profile.contact_number}"
            else:
                tech_details = "Not Assigned"

            print("service_subject:",service.service_subject )
            print("tech_details",tech_details)
            # Mapping placeholders
            placeholders = {
                "customer_name": customer.fullname,
                "service_date": service.service_date.strftime("%d-%m-%Y"),
                "delivery_time": service.delivery_time.strftime("%I:%M %p"),
                "selected_service": service.service_subject,
                "tech_details": tech_details,
            }

            # Render body
            email_body = email_template.body
            for key, value in placeholders.items():
                email_body = email_body.replace(f"{{{key}}}", str(value))

            # Subject
            subject = "Service Appointment Confirmation – Seva Facility Services"
            if not created:
                subject = "Service Appointment Updated – Seva Facility Services"

            send_email_task.delay(
                subject,
                email_body,
                recipient=customer.primaryemail,
                attachment_path=None,
                attachment_name=None,
            )
            print("📧 Email task queued for:", customer.primaryemail)

    # ---------------- WhatsApp ----------------
    if customer.primarycontact:
        whatsapp_template = MessageTemplates.objects.filter(
            message_type="whatsapp", category="service"
        ).first()
        if whatsapp_template:
            whatsapp_body = whatsapp_template.body
            for key, value in placeholders.items():
                whatsapp_body = whatsapp_body.replace(f"{{{key}}}", str(value))

            mobile = f"91{customer.primarycontact}"
            send_whatsapp_task.delay(mobile, whatsapp_body)
            print("📲 WhatsApp task queued for:", mobile)



# @receiver(service_scheduled)
# def send_service_scheduled_email(sender, service_id, created, **kwargs):
#     from .models import service_management, MessageTemplates
   
#     service = service_management.objects.get(id=service_id)
#     customer = getattr(service, "customer", None)
    
#     if not customer or not customer.primaryemail:
#         return

#     template = MessageTemplates.objects.filter(message_type = "email",category="service").first()
#     print('email', template)
#     if not template:
#         return
    
#     # Pick first technician
#     techwork = service.techworklist_set.order_by("id").first()
#     if techwork:
#         tech_user = techwork.technician
#         try:
#             profile = TechnicianProfile.objects.get(user=tech_user)
#             tech_details = f"{profile.first_name} {profile.last_name} - {profile.contact_number}"
#         except TechnicianProfile.DoesNotExist:
#             tech_details = f"{tech_user.first_name} {tech_user.last_name}"
#     else:
#         tech_details = "Not Assigned"

#     # Mapping placeholders
#     placeholders = {
#         "customer_name": customer.fullname,
#         "service_date": service.service_date.strftime("%d-%m-%Y"),
#         "delivery_time": service.delivery_time.strftime("%I:%M %p"),
#         "selected_services": service.service_subject,
#         "tech_details": tech_details,
#     }

#     body = template.body
#     for key, value in placeholders.items():
#         body = body.replace(f"{{{key}}}", str(value))

#     # Subject can differ for creation vs update
#     subject = "Service Appointment Confirmation – Seva Facility Services"
#     if not created:
#         subject = "Service Appointment Updated – Seva Facility Services"

#     send_email_task.delay(subject, body, recipient = customer.primaryemail,attachment_path=None, attachment_name=None)
#     print("📧 Email task queued for:", customer.primaryemail)

#     whatsapp_msg = (
#         f"Hello {customer.fullname}, your service is scheduled on "
#         f"{service.service_date.strftime('%d-%m-%Y')} at {service.delivery_time.strftime('%I:%M %p')}."
#     )
#     mobile = f"91{customer.primarycontact}"
#     send_whatsapp_task.delay(mobile, whatsapp_msg)
#     print("📲 WhatsApp task queued for:", mobile)
