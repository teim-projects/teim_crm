from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_service_email(subject, message, recipient):
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [recipient],
        fail_silently=False,
    )
    return f"Email sent to {recipient}"
