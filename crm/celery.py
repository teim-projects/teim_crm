from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from django.conf import settings
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm.settings')

app = Celery('crm')


app.conf.update(timezone='Asia/Kolkata')

app.config_from_object('django.conf:settings', namespace='CELERY')


# Celery Beat Settings
# app.conf.beat_schedule = {
#     'send-mail-every-day-at-8' : {
#         'task':'email_sender.tasks.send_mail_func',
#         'schedule':crontab(minute='*/1'),
#         # 'args' : '2'
#     }
# }


# CELERY BEAT SCHEDULES

app.conf.beat_schedule = {
    'send-hot-lead-emails-every-7-days': {
        'task': 'email_sender.tasks.send_hot_lead_emails',
        'schedule': crontab(minute=12,hour=11), 
    },
    
    'send-warm-lead-emails-weekly': {
        'task': 'email_sender.tasks.send_warm_lead_emails',
        'schedule': crontab(0, 0, day_of_week='monday'),  
    },

    'send-cold-lead-emails-every-15-days': {
        'task': 'email_sender.tasks.send_cold_lead_emails',
        'schedule': crontab(0, 0, day_of_month='1,15'), 
    },
}

# ////////////////////////////////////////////////////


app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
