# signals.py
import requests
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver, Signal
from django.db import transaction
from django.contrib.auth.models import User
from .models import UserProfile, TechWorkList, TechnicianProfile, service_management,WorkAllocation,MessageTemplates
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

# # Signal: triggered when customer should be notified
# service_scheduled = Signal()

# @receiver(post_save, sender=WorkAllocation)
# def notify_customer_on_workallocation(sender, instance, created, **kwargs):
#     """
#     Trigger notification only when a work allocation is created.
#     """

#     print("signall is called..........")
#     if not created:
#         return  # skip updates

#     service = instance.service
#     print("service_id",service.id)
#     if not service or not service.customer_id:
#         return

#     transaction.on_commit(lambda: service_scheduled.send(
#         sender=WorkAllocation,
#         service_id=service.id,
#         created=created    
#     ))

# @receiver(m2m_changed, sender=WorkAllocation.technician.through)
# def workallocation_technicians_changed(sender, instance, action, **kwargs):
#     """
#     Trigger notification after technicians are added/removed.
#     """
#     if action == "post_add":
#         print(f"👷 Techs assigned to WorkAllocation {instance.id}")
#         service = instance.service
#         if not service or not service.customer_id:
#             return

#         transaction.on_commit(lambda: service_scheduled.send(
#             sender=WorkAllocation,
#             service_id=service.id,
#             created=False  # since allocation already exists
#         ))







# @receiver(service_scheduled)
# def send_service_scheduled_email(sender, service_id, created, **kwargs):
#     from .models import service_management, MessageTemplates,WorkAllocation
#     service = service_management.objects.get(id=service_id)
#     customer = getattr(service, "customer", None)
#     print('call')
#     if not customer:
#         return

#     # ---------------- Email ----------------
#     if customer.primaryemail:
#         email_template = MessageTemplates.objects.filter(
#             message_type="email", category="service"
#         ).first()
#         if email_template:
#             # Pick first technician
#            # Pick first technician from WorkAllocation
#             work = WorkAllocation.objects.filter(service=service_id).first()
#             if work and work.technician.exists():
#                 tech_profile = work.technician.first()  # ManyToMany
#                 tech_details = f"{tech_profile.first_name} {tech_profile.last_name} - {tech_profile.contact_number}"
#             else:
#                 tech_details = "Not Assigned"

#             print("service_subject:",service.service_subject )
#             print("tech_details",tech_details)
#             # Mapping placeholders
#             placeholders = {
#                 "customer_name": customer.fullname,
#                 "service_date": service.service_date.strftime("%d-%m-%Y"),
#                 "delivery_time": service.delivery_time.strftime("%I:%M %p"),
#                 "selected_service": service.service_subject,
#                 "tech_details": tech_details,
#             }

#             # Render body
#             email_body = email_template.body
#             for key, value in placeholders.items():
#                 email_body = email_body.replace(f"{{{key}}}", str(value))

#             # Subject
#             subject = "Service Appointment Confirmation – Seva Facility Services"
#             if not created:
#                 subject = "Service Appointment Updated – Seva Facility Services"

#             send_email_task.delay(
#                 subject,
#                 email_body,
#                 recipient=customer.primaryemail,
#                 attachment_path=None,
#                 attachment_name=None,
#             )
#             print("📧 Email task queued for:", customer.primaryemail)

#     # ---------------- WhatsApp ----------------
#     if customer.primarycontact:
#         whatsapp_template = MessageTemplates.objects.filter(
#             message_type="whatsapp", category="service"
#         ).first()
#         if whatsapp_template:
#             whatsapp_body = whatsapp_template.body
#             for key, value in placeholders.items():
#                 whatsapp_body = whatsapp_body.replace(f"{{{key}}}", str(value))

#             mobile = f"91{customer.primarycontact}"
#             send_whatsapp_task.delay(mobile, whatsapp_body)
#             print("📲 WhatsApp task queued for:", mobile)


# Custom signal triggered when customer should be notified
service_scheduled = Signal()

# ------------------- Post-save signal -------------------
@receiver(post_save, sender=WorkAllocation)
def notify_customer_on_workallocation(sender, instance, created, **kwargs):
    """
    Trigger notification only when a WorkAllocation is created.
    We do NOT send it here if techs are not yet assigned.
    """
    if not created:
        return  # only trigger on creation

    # Do nothing here; wait until technicians are assigned
    print(f"WorkAllocation {instance.id} created. Waiting for technicians...")

# ------------------- M2M signal -------------------
@receiver(m2m_changed, sender=WorkAllocation.technician.through)
def workallocation_technicians_changed(sender, instance, action, pk_set, **kwargs):
    """
    Trigger notification after technicians are assigned.
    """
    if action != "post_add" or not pk_set:
        return

    service = instance.service
    if not service or not service.customer_id:
        return

    print(f"Technicians assigned to WorkAllocation {instance.id}: {pk_set}")

    # Trigger the custom signal once all technicians are added
    transaction.on_commit(lambda: service_scheduled.send(
        sender=WorkAllocation,
        service_id=service.id,
        created=True  # treat as "new allocation" notification
    ))

# ------------------- Notification handler -------------------
@receiver(service_scheduled)
def send_service_scheduled_email(sender, service_id, created, **kwargs):
    """
    Sends Email + WhatsApp notification to customer
    """
    service = service_management.objects.get(id=service_id)
    customer = getattr(service, "customer", None)
    if not customer:
        return

    # ------------------- Collect tech details -------------------
    work = WorkAllocation.objects.filter(service=service_id).order_by("-id").first()
    if work and work.technician.exists():
        tech_list = [
            f"{t.first_name} {t.last_name} - {t.contact_number}"
            for t in work.technician.all()
        ]
        tech_details = ", ".join(tech_list)
    else:
        tech_details = "Not Assigned"

    placeholders = {
        "customer_name": customer.fullname,
        "service_date": service.service_date.strftime("%d-%m-%Y"),
        "delivery_time": service.delivery_time.strftime("%I:%M %p"),
        "selected_service": service.service_subject,
        "tech_details": tech_details,
    }

    # ------------------- Email -------------------
    if customer.primaryemail:
        email_template = MessageTemplates.objects.filter(
            message_type="email", category="service"
        ).first()
        if email_template:
            email_body = email_template.body
            for key, value in placeholders.items():
                email_body = email_body.replace(f"{{{key}}}", str(value))

            subject = (
                "Service Appointment Confirmation – Seva Facility Services"
                if created else
                "Service Appointment Updated – Seva Facility Services"
            )

            send_email_task.delay(
                subject,
                email_body,
                recipient=customer.primaryemail,
                attachment_path=None,
                attachment_name=None,
            )
            print("📧 Email queued for:", customer.primaryemail)

    # ------------------- WhatsApp -------------------
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
            print("📲 WhatsApp queued for:", mobile)
  
