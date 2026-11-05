import logging

import redis
from django.conf import settings
from django.db import transaction
from django.db.models.signals import (
    post_save,
    post_delete,
    pre_save,
    m2m_changed,
)
from django.dispatch import receiver

from crmapp.models import (
    customer_details,
    quotation_management,
    ServiceProduct,
    service_management,
    TechWorkList,
)
from crmapp.tasks import refresh_customer_recommendations

logger = logging.getLogger(__name__)


def schedule_customer_refresh(customer_id):

    if not customer_id:
        return

    try:
        client = redis.Redis.from_url(
            settings.CELERY_BROKER_URL
        )

        # Combine rapid events for the same customer.
        key = f"crm:recommendation:pending:{customer_id}"

        scheduled = client.set(
            key,
            "1",
            nx=True,
            ex=10,
        )

        if scheduled:
            refresh_customer_recommendations.apply_async(
                args=[str(customer_id)],
                countdown=10,
            )

    except Exception:
        # Recommendation failures must not interrupt CRM operations.
        logger.exception(
            "Could not schedule recommendation refresh for customer %s",
            customer_id,
        )


def schedule_after_commit(customer_id):
    if customer_id:
        transaction.on_commit(
            lambda: schedule_customer_refresh(customer_id)
        )


# ------------------------------------------------------------
# 1. QUOTATION PRODUCT CHANGES
# ------------------------------------------------------------

@receiver(
    m2m_changed,
    sender=quotation_management.selected_services.through,
)
def quotation_products_changed(
    sender,
    instance,
    action,
    **kwargs,
):

    if action not in ("post_add", "post_remove", "post_clear"):
        return

    if not instance.is_latest:
        return

    schedule_after_commit(instance.customer_id)


# ------------------------------------------------------------
# 2. SERVICE PRODUCT ADDED, UPDATED OR DELETED
# ------------------------------------------------------------

@receiver(post_save, sender=ServiceProduct)
def service_product_saved(sender, instance, **kwargs):

    customer_id = (
        service_management.objects
        .filter(pk=instance.service_id)
        .values_list("customer_id", flat=True)
        .first()
    )

    schedule_after_commit(customer_id)


@receiver(post_delete, sender=ServiceProduct)
def service_product_deleted(sender, instance, **kwargs):

    customer_id = (
        service_management.objects
        .filter(pk=instance.service_id)
        .values_list("customer_id", flat=True)
        .first()
    )

    schedule_after_commit(customer_id)


# ------------------------------------------------------------
# 3. SERVICE APPROVAL STATUS CHANGED
# ------------------------------------------------------------

@receiver(pre_save, sender=service_management)
def capture_previous_service_approval(
    sender,
    instance,
    **kwargs,
):

    if not instance.pk:
        instance._previous_recommendation_approval = None
        return

    instance._previous_recommendation_approval = (
        sender.objects
        .filter(pk=instance.pk)
        .values_list("is_approved", flat=True)
        .first()
    )


@receiver(post_save, sender=service_management)
def service_approval_changed(
    sender,
    instance,
    created,
    **kwargs,
):

    previous = getattr(
        instance,
        "_previous_recommendation_approval",
        None,
    )

    if not created and previous != instance.is_approved:
        schedule_after_commit(instance.customer_id)


# ------------------------------------------------------------
# 4. TECHNICIAN WORKLIST BECOMES COMPLETED
# ------------------------------------------------------------

@receiver(pre_save, sender=TechWorkList)
def capture_previous_worklist_status(
    sender,
    instance,
    **kwargs,
):

    if not instance.pk:
        instance._previous_recommendation_status = None
        return

    instance._previous_recommendation_status = (
        sender.objects
        .filter(pk=instance.pk)
        .values_list("status", flat=True)
        .first()
    )


@receiver(post_save, sender=TechWorkList)
def worklist_completed(
    sender,
    instance,
    created,
    **kwargs,
):

    previous = getattr(
        instance,
        "_previous_recommendation_status",
        None,
    )

    became_completed = (
        instance.status == "Completed"
        and (
            created
            or previous != "Completed"
        )
    )

    if not became_completed or not instance.service_id:
        return

    customer_id = (
        service_management.objects
        .filter(pk=instance.service_id)
        .values_list("customer_id", flat=True)
        .first()
    )

    schedule_after_commit(customer_id)

# ------------------------------------------------------------
# 5. NEW CUSTOMER CREATED
# ------------------------------------------------------------

@receiver(post_save, sender=customer_details)
def new_customer_created(sender, instance, created, **kwargs):

    if not created:
        return

    schedule_after_commit(instance.pk)
