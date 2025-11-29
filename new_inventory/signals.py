
# signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
from django.utils import timezone

from .models import (
    GoodsReceiveNoteItem, GoodsReceiveNote,
    CurrentStock, StockLedger, ProductStock
)

def _effective_qty(item):
    val = getattr(item, 'accepted_qty', None)
    if val is None:
        val = getattr(item, 'received_qty', None) or Decimal('0.00')
    return Decimal(val or 0)

@receiver(pre_save, sender=GoodsReceiveNoteItem)
def grn_item_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = GoodsReceiveNoteItem.objects.get(pk=instance.pk)
            instance._old_received_qty = _effective_qty(old)
            instance._old_batch_id = old.batch_id
            instance._old_grn_id = old.grn_id
        except GoodsReceiveNoteItem.DoesNotExist:
            instance._old_received_qty = Decimal('0')
            instance._old_batch_id = None
            instance._old_grn_id = None
    else:
        instance._old_received_qty = Decimal('0')
        instance._old_batch_id = None
        instance._old_grn_id = None

@receiver(post_save, sender=GoodsReceiveNoteItem)
def grn_item_post_save(sender, instance, created, **kwargs):
    new_qty = _effective_qty(instance)
    old_qty = Decimal(getattr(instance, "_old_received_qty", 0) or 0)
    delta = new_qty - old_qty  # positive -> net IN, negative -> net OUT

    # Nothing changed and nothing to do
    if delta == 0 and not created:
        # still ensure ledger exists/consistency if you need,
        # but skip stock adjustments
        return

    with transaction.atomic():
        # lock GRN to get destination (location) safely
        grn = None
        try:
            grn = GoodsReceiveNote.objects.select_for_update().get(pk=instance.grn_id)
        except GoodsReceiveNote.DoesNotExist:
            grn = None

        location_type = grn.destination_type if grn else None
        location_id = grn.destination_id if grn else None

        # -- handle move from old batch/location (if batch or destination changed)
        old_batch_id = getattr(instance, "_old_batch_id", None)
        old_grn_id = getattr(instance, "_old_grn_id", None)
        old_location_type = None
        old_location_id = None
        if old_grn_id:
            try:
                old_grn = GoodsReceiveNote.objects.get(pk=old_grn_id)
                old_location_type = old_grn.destination_type
                old_location_id = old_grn.destination_id
            except GoodsReceiveNote.DoesNotExist:
                old_location_type = None
                old_location_id = None

        # If old qty existed and batch/location changed, subtract old from old CurrentStock & ProductStock
        if old_qty and (old_batch_id != instance.batch_id or old_location_type != location_type or old_location_id != location_id):
            # CurrentStock decrement on old row
            cs_old_qs = CurrentStock.objects.select_for_update().filter(
                product=instance.product_id,
                batch_id=old_batch_id,
                location_type=old_location_type,
                location_id=old_location_id
            )
            if cs_old_qs.exists():
                cs_old = cs_old_qs.first()
                cs_old.in_qty = (cs_old.in_qty or Decimal('0')) - Decimal(old_qty)
                cs_old.closing_qty = (cs_old.opening_qty or Decimal('0')) + (cs_old.in_qty or Decimal('0')) - (cs_old.out_qty or Decimal('0')) - (cs_old.reserved_qty or Decimal('0'))
                cs_old.last_updated = timezone.now()
                cs_old.save()

            # ProductStock decrement on old product/location
            ps_old_qs = ProductStock.objects.select_for_update().filter(
                product=instance.product_id,
                location_type=old_location_type,
                location_id=old_location_id
            )
            if ps_old_qs.exists():
                ps_old = ps_old_qs.first()
                # moving old received -> treat as reducing total_in_qty (we assume it was previously added as IN)
                ps_old.total_in_qty = (ps_old.total_in_qty or Decimal('0')) - Decimal(old_qty)
                ps_old.save()

            # remove / create reversal ledger entries if your ledger strategy requires

        # -- apply delta to current (new) CurrentStock & ProductStock
        if delta != 0:
            # CurrentStock update (per batch)
            cs_qs = CurrentStock.objects.select_for_update().filter(
                product=instance.product,
                batch=instance.batch,
                location_type=location_type,
                location_id=location_id
            )
            if cs_qs.exists():
                cs = cs_qs.first()
            else:
                cs = CurrentStock.objects.create(
                    product=instance.product,
                    batch=instance.batch,
                    location_type=location_type,
                    location_id=location_id,
                    opening_qty=Decimal('0.000'),
                    in_qty=Decimal('0.000'),
                    out_qty=Decimal('0.000'),
                    reserved_qty=Decimal('0.000'),
                    closing_qty=Decimal('0.000')
                )

            # apply delta to CurrentStock in_qty
            cs.in_qty = (cs.in_qty or Decimal('0')) + Decimal(delta)
            cs.closing_qty = (cs.opening_qty or Decimal('0')) + (cs.in_qty or Decimal('0')) - (cs.out_qty or Decimal('0')) - (cs.reserved_qty or Decimal('0'))
            cs.last_updated = timezone.now()
            cs.save()

            # ProductStock update (aggregate per product/location)
            ps_qs = ProductStock.objects.select_for_update().filter(
                product=instance.product,
                location_type=location_type,
                location_id=location_id
            )
            if ps_qs.exists():
                ps = ps_qs.first()
            else:
                ps = ProductStock.objects.create(
                    product=instance.product,
                    location_type=location_type,
                    location_id=location_id,
                    total_in_qty=Decimal('0.000'),
                    total_out_qty=Decimal('0.000'),
                    total_reserved_qty=Decimal('0.000')
                )

            # If delta > 0 treat as additional IN, else treat as additional OUT
            if delta > 0:
                ps.total_in_qty = (ps.total_in_qty or Decimal('0')) + Decimal(delta)
            else:
                ps.total_out_qty = (ps.total_out_qty or Decimal('0')) + (-Decimal(delta))

            ps.save()

            # ledger entry
            StockLedger.objects.filter(transaction_ref=f"GRN_ITEM_{instance.pk}").delete()
            if delta > 0:
                in_qty_val = Decimal(delta)
                out_qty_val = Decimal('0')
            else:
                in_qty_val = Decimal('0')
                out_qty_val = -Decimal(delta)

            StockLedger.objects.create(
                product=instance.product,
                batch=instance.batch,
                location_type=location_type,
                location_id=location_id,
                transaction_type='GRN_IN',
                transaction_ref=f"GRN_ITEM_{instance.pk}",
                document_id=instance.grn_id,
                in_qty=in_qty_val,
                out_qty=out_qty_val,
                balance_qty=cs.closing_qty,
                transaction_date=grn.received_date if grn else timezone.now().date(),
                created_by=None,
                remarks=instance.remarks or f"GRN {instance.grn_id} item {instance.pk}"
            )

@receiver(post_delete, sender=GoodsReceiveNoteItem)
def grn_item_post_delete(sender, instance, **kwargs):
    old_qty = _effective_qty(instance)
    if not old_qty:
        return

    with transaction.atomic():
        try:
            grn = GoodsReceiveNote.objects.get(pk=instance.grn_id)
            location_type = grn.destination_type
            location_id = grn.destination_id
        except GoodsReceiveNote.DoesNotExist:
            location_type = None
            location_id = None

        # CurrentStock decrement
        cs_qs = CurrentStock.objects.select_for_update().filter(
            product=instance.product,
            batch=instance.batch,
            location_type=location_type,
            location_id=location_id
        )
        if cs_qs.exists():
            cs = cs_qs.first()
            cs.in_qty = (cs.in_qty or Decimal('0')) - Decimal(old_qty)
            cs.closing_qty = (cs.opening_qty or Decimal('0')) + (cs.in_qty or Decimal('0')) - (cs.out_qty or Decimal('0')) - (cs.reserved_qty or Decimal('0'))
            cs.last_updated = timezone.now()
            cs.save()

        # ProductStock decrement
        ps_qs = ProductStock.objects.select_for_update().filter(
            product=instance.product,
            location_type=location_type,
            location_id=location_id
        )
        if ps_qs.exists():
            ps = ps_qs.first()
            # assume previously it was counted as in; subtract from total_in_qty
            ps.total_in_qty = (ps.total_in_qty or Decimal('0')) - Decimal(old_qty)
            ps.save()

        # delete ledger entries for this GRN item
        StockLedger.objects.filter(transaction_ref=f"GRN_ITEM_{instance.pk}").delete()
