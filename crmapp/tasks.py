from celery import shared_task
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
import os
import requests
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
def send_email_task(subject, message, recipient, attachment_path=None, attachment_name=None ):
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
        
    )
    # email.content_subtype = "html"
    # Attach file if provided
    if attachment_path and os.path.exists(attachment_path):
        email.attach_file(attachment_path)

    email.send(fail_silently=False)
    return f"Email sent to {recipient}"



# @shared_task
# def send_whatsapp_task(mobile, msg):
#     # Keep authKey in URL
#     whatsapp_api = settings.WHATSAPP_API 
#     # Rest of fields in form-data
#     payload = {
#         "channelId": settings.WHATSAPP_CHANNEL_ID ,        # must match your authKey’s channel
#         "mobile": str(mobile),       # must include country code (91XXXXXXXXXX)
#         "msg": msg
#     }

#     try:
#         response = requests.post(whatsapp_api, data=payload)  # send as form-data

#         if response.status_code == 200:
#             print("✅ WhatsApp Message Send....")
#         else:
#             print("❌ WhatsApp API error:", response.status_code, response.text)

#     except Exception as e:
#         print("⚠️ WhatsApp send failed:", str(e))

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
                mime_type = "application/octet-stream"

        payload.update({
            "fileUrl": attachment_path,        # must be accessible via URL
            "fileName": attachment_name,       # keep full name with extension
            "fileType": file_type,
            "mimeType": mime_type,
            
        })

    try:
        response = requests.post(whatsapp_api, json=payload)  # ✅ use json, not data
        if response.status_code == 200:
            print("✅ WhatsApp Message Sent")
        else:
            print("❌ WhatsApp API error:", response.status_code, response.text)
    except Exception as e:
        print("⚠️ WhatsApp send failed:", str(e))




        