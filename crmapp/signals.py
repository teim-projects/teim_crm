# signals.py
import requests
from django.db.models.signals import post_save, m2m_changed,  pre_delete
from django.dispatch import receiver, Signal
from django.db import transaction
from django.contrib.auth.models import User
from .models import UserProfile, TechWorkList, TechnicianProfile, service_management,WorkAllocation,MessageTemplates, SalesPerson,lead_management
from crmapp.tasks import send_email_task,send_whatsapp_task


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(pre_delete, sender=SalesPerson)
def preserve_salesperson_leads(sender, instance, **kwargs):
    user = User.objects.filter(username=instance.mobile_no).first()
    user_id = user.id if user else None
    lead_management.objects.filter(salesperson=instance).update(
        old_salesperson_id=user_id,
        salesperson=None
    )


@receiver(post_save, sender=TechWorkList)
def mark_new_work_as_notification(sender, instance, created, **kwargs):
    # print('mark_new_work_as_notification')
    if created:
        # Mark as notified internally
        instance.is_notified = True
        instance.save(update_fields=['is_notified'])



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
  
