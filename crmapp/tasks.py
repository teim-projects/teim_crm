from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import os
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

@shared_task
def send_email_task(subject, message, recipient, attachment_path=None, attachment_name=None):
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    email.content_subtype = "html"
    # Attach file if provided
    if attachment_path and os.path.exists(attachment_path):
        email.attach_file(attachment_path)

    email.send(fail_silently=False)
    return f"Email sent to {recipient}"


