from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

# Initialize Celery
app = Celery('crm')

# Load settings with CELERY_ prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in apps
app.autodiscover_tasks()

# Timezone
app.conf.timezone = 'Asia/Kolkata'

# Beat Schedules
app.conf.beat_schedule = {
    'send-hot-lead-emails-every-day-11-12': {
        'task': 'email_sender.tasks.send_hot_lead_emails',
        'schedule': crontab(minute=12, hour=11),  # every day at 11:12 AM
    },
    'send-warm-lead-emails-weekly': {
        'task': 'email_sender.tasks.send_warm_lead_emails',
        'schedule': crontab(minute=0, hour=0, day_of_week='monday'),  # every Monday at midnight
    },
    'send-cold-lead-emails-every-15-days': {
        'task': 'email_sender.tasks.send_cold_lead_emails',
        'schedule': crontab(minute=0, hour=0, day_of_month='1,15'),  # 1st & 15th at midnight
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
