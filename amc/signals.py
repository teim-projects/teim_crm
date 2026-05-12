from django.db.models.signals import post_save
from django.dispatch import receiver
from amc.models import AMCServiceSchedule, AMCServiceVisit

@receiver(post_save, sender=AMCServiceSchedule)
def sync_amc_to_service(sender, instance, **kwargs):

    visit = AMCServiceVisit.objects.filter(
        amc=instance.amc,
        service_date=instance.service_date
    ).first()

    if visit and visit.crm_service:
        visit.crm_service.is_approved = instance.is_approved
        visit.crm_service.save()