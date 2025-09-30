from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import os
import requests
from .models import  PaymentsRecord
from django.utils import timezone
from datetime import timedelta

# @shared_task
# def send_email_task(subject, message, recipient):
#     send_mail(
#         subject,
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         recipient_list = [recipient],
#         fail_silently=False,
#     )
#     return f"Email sent to {recipient}"

# @shared_task
# def send_email_task(subject, message, recipient, attachment_path=None, attachment_name=None ):
#     email = EmailMessage(
#         subject=subject,
#         body=message,
#         from_email=settings.DEFAULT_FROM_EMAIL,
#         to=[recipient],
        
#     )
#     # email.content_subtype = "html"
#     # Attach file if provided
#     if attachment_path and os.path.exists(attachment_path):
#         email.attach_file(attachment_path)

#     email.send(fail_silently=False)
#     return f"Email sent to {recipient}"

@shared_task
def send_email_task(subject, message, recipient, attachment_path=None, attachment_name=None):
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )

    # Attach file if provided
    if attachment_path:
        if attachment_path.startswith("http"):  # URL case
            try:
                response = requests.get(attachment_path, allow_redirects=True)
                if response.status_code == 200:
                    email.attach(
                        attachment_name,
                        response.content,
                        "application/pdf"
                    )
            except Exception as e:
                print("⚠️ Failed to download attachment:", e)
        elif os.path.exists(attachment_path):  # local file case
            email.attach_file(attachment_path)

    email.send(fail_silently=False)
    return f"Email sent to {recipient}"

import mimetypes
@shared_task
def send_whatsapp_task(mobile, msg, attachment_path=None, attachment_name=None):
    whatsapp_api = settings.WHATSAPP_API
    payload = {
        "channelId": settings.WHATSAPP_CHANNEL_ID,
        "mobile": str(mobile),
        "msg": msg,
    }

    if attachment_path and attachment_name:
        ext = attachment_name.split('.')[-1].lower()
        file_type_map = {
            'jpg': 'image', 'jpeg': 'image', 'png': 'image', 'gif': 'image',
            'pdf': 'document', 'doc': 'document', 'docx': 'document',
            'xls': 'document', 'xlsx': 'document', 'ppt': 'document',
            'pptx': 'document', 'txt': 'document', 'zip': 'document',
            'rar': 'document', 'vcf': 'document',
            'mp3': 'audio', 'mp4': 'video', 'avi': 'video', 'mov': 'video'
        }
        file_type = file_type_map.get(ext, 'document')

        # ✅ Correct MIME type
        mime_type, _ = mimetypes.guess_type(attachment_name)
        if not mime_type:
            # fallback defaults
            if file_type == "image":
                mime_type = f"image/{ext}"
            elif file_type == "audio":
                mime_type = f"audio/{ext}"
            elif file_type == "video":
                mime_type = f"video/{ext}"
            else:
                mime_type = "application/pdf"

        payload.update({
            "fileUrl": attachment_path,        # must be accessible via URL
            "fileName": attachment_name,       # keep full name with extension
            "fileType": file_type,
            "mimeType": mime_type,  
        })

    try:
        response = requests.post(whatsapp_api, json=payload)  # ✅ use json, not data
        if response.status_code == 200:
            print("✅ WhatsApp Message Sent",mobile)
        else:
            print("❌ WhatsApp API error:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ WhatsApp send failed:", str(e))



@shared_task
def send_due_payment_alerts():
    today = timezone.now().date()
    upcoming = today + timedelta(days=2)
    print(f"[DEBUG] Today: {today}, Upcoming: {upcoming}")

    due_payments = PaymentsRecord.objects.filter(
        next_due_date__gte=today,
        next_due_date__lte=upcoming,
        amount_remaining__gt=0
    )
    print(f"[DEBUG] Due payments found: {due_payments.count()}")

    for payment in due_payments:
        print(f"[DEBUG] Processing payment: {payment.payment_invoice_no}")

        # avoid duplicate alerts for the same day
        if payment.last_alert_sent == today:
            print(f"[DEBUG] Skipping {payment.payment_invoice_no}, alert already sent today")
            continue  

        customer = getattr(payment.main_invoice, "customer", None)
        if not customer:
            print(f"[DEBUG] Payment {payment.payment_invoice_no} has no customer assigned")
            continue

        email = getattr(customer, "primaryemail", None)
        mobile = getattr(customer, "primarycontact", None)
        print(f"[DEBUG] Customer email: {email}, mobile: {mobile}")

        n_m = f"91{mobile}" if mobile else None
        subject = f"Payment Due Reminder: {payment.payment_invoice_no}"
        message = (
            f"Dear {getattr(customer, 'fullname', 'Customer')},\n\n"
            f"This is a reminder that your payment of {payment.amount_remaining} "
            f"is due on {payment.next_due_date} for invoice {payment.main_invoice.tax_invoice_no}.\n\n"
            "Please ensure timely payment.\n\nThank you."
        )

        if email:
            print(f"[DEBUG] Sending email to {email}")
            send_email_task.delay(subject, message, email)
        else:
            print(f"[DEBUG] No email for payment {payment.payment_invoice_no}")

        if n_m:
            print(f"[DEBUG] Sending WhatsApp to {n_m}")
            whatsapp_msg = (
                f"Reminder: Your payment of {payment.amount_remaining} "
                f"is due on {payment.next_due_date} for invoice {payment.main_invoice.tax_invoice_no}."
            )
            send_whatsapp_task.delay(n_m, whatsapp_msg)
        else:
            print(f"[DEBUG] No mobile for payment {payment.payment_invoice_no}")

        payment.last_alert_sent = today
        payment.save(update_fields=["last_alert_sent"])
        print(f"[DEBUG] Updated last_alert_sent for {payment.payment_invoice_no}")

