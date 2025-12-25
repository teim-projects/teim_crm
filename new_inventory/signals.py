
# signals.py
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from decimal import Decimal
from django.utils import timezone

from .models import (
    GoodsReceiveNoteItem, GoodsReceiveNote,
    CurrentStock, StockLedger, ProductStock ,MaterialTransferNote, MTNItem , MaterialRequest, Notification
)

from crmapp.models import BranchManager
from django.contrib.auth.models import User

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





# @receiver(post_save, sender=MaterialTransferNote)
# def handle_mtn_stock_movement(sender, instance, **kwargs):
#     """
#     Triggers stock movement only when status is changed to 'APPROVED'.
#     Prevents duplicate processing by checking a local flag or specific status flow.
#     """
#     if instance.status == "APPROVED":
#         with transaction.atomic():
#             items = instance.items.all()
#             for item in items:
#                 # 1. DEDUCT FROM SOURCE
#                 _update_stock_logic(
#                     product=item.product,
#                     batch=item.batch,
#                     loc_type=instance.source_type,
#                     loc_id=instance.source_id,
#                     qty=-item.transfer_qty, # Negative for OUT
#                     trans_type="MTN_OUT",
#                     ref=f"MTN_ITEM_{item.id}",
#                     doc_id=instance.id
#                 )
                
#                 # 2. ADD TO DESTINATION
#                 _update_stock_logic(
#                     product=item.product,
#                     batch=item.batch,
#                     loc_type=instance.destination_type,
#                     loc_id=instance.destination_id,
#                     qty=item.transfer_qty, # Positive for IN
#                     trans_type="MTN_IN",
#                     ref=f"MTN_ITEM_{item.id}",
#                     doc_id=instance.id
#                 )


@receiver(pre_save, sender=MTNItem)
def mtn_item_pre_save(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = MTNItem.objects.get(pk=instance.pk)
            instance._old_transfer_qty = Decimal(old.transfer_qty or 0)
        except MTNItem.DoesNotExist:
            instance._old_transfer_qty = Decimal('0')
    else:
        instance._old_transfer_qty = Decimal('0')



def _update_stock_logic(product, batch, loc_type, loc_id, qty, trans_type, ref, doc_id):
    """
    Helper function to update CurrentStock, ProductStock, and Ledger.
    """
    # Update CurrentStock (Batch level)
    cs, _ = CurrentStock.objects.get_or_create(
        product=product, batch=batch, 
        location_type=loc_type, location_id=loc_id
    )
    
    if qty > 0:
        cs.in_qty += Decimal(qty)
    else:
        cs.out_qty += abs(Decimal(qty))
    
    cs.recompute_closing()

    # Update ProductStock (Aggregate level)
    ps, _ = ProductStock.objects.get_or_create(
        product=product, location_type=loc_type, location_id=loc_id
    )
    if qty > 0:
        ps.total_in_qty += Decimal(qty)
    else:
        ps.total_out_qty += abs(Decimal(qty))
    ps.save()
  
    # Create Ledger Entry
    StockLedger.objects.create(
        product=product,
        batch=batch,
        location_type=loc_type,
        location_id=loc_id,
        transaction_type=trans_type,
        transaction_ref=ref,
        document_id=doc_id,
        in_qty=qty if qty > 0 else 0,
        out_qty=abs(qty) if qty < 0 else 0,
        balance_qty=cs.closing_qty
    )


@receiver(post_save, sender=MTNItem)
def handle_mtn_item_reservation(sender, instance, created, **kwargs):
    mtn = instance.mtn

    if mtn.status != 'DRAFT':
        return

    new_qty = Decimal(instance.transfer_qty or 0)
    old_qty = Decimal(getattr(instance, "_old_transfer_qty", 0))
    delta = new_qty - old_qty

    if delta == 0:
        return

    with transaction.atomic():
        # ----- CurrentStock (Batch level) -----
        cs = CurrentStock.objects.select_for_update().get(
            product=instance.product,
            batch=instance.batch,
            location_type=mtn.source_type,
            location_id=mtn.source_id
        )

        cs.reserved_qty += delta
        cs.recompute_closing()

        # ----- ProductStock (Aggregate level) -----
        ps = ProductStock.objects.select_for_update().get(
            product=instance.product,
            location_type=mtn.source_type,
            location_id=mtn.source_id
        )

        ps.total_reserved_qty += delta
        ps.save()

@receiver(pre_save, sender=MaterialTransferNote)
def handle_mtn_status_change(sender, instance, **kwargs):
    """
    Handles the transition from DRAFT -> APPROVED.
    Converts 'Reserved' stock into 'Out/In' movement.
    """
    if not instance.pk:
        return

    try:
        old_instance = MaterialTransferNote.objects.get(pk=instance.pk)
    except MaterialTransferNote.DoesNotExist:
        return

    # Transition: DRAFT -> APPROVED
    if old_instance.status == 'DRAFT' and instance.status == 'APPROVED':
        with transaction.atomic():
            for item in instance.items.all():
                # --- SOURCE SIDE: MOVE FROM RESERVED TO OUT ---
                cs_source = CurrentStock.objects.select_for_update().get(
                    product=item.product, batch=item.batch,
                    location_type=instance.source_type, location_id=instance.source_id
                )
                cs_source.reserved_qty -= item.transfer_qty
                cs_source.out_qty += item.transfer_qty
                cs_source.recompute_closing()

                ps_source = ProductStock.objects.select_for_update().get(
                    product=item.product, location_type=instance.source_type, location_id=instance.source_id
                )
                ps_source.total_reserved_qty -= item.transfer_qty
                ps_source.total_out_qty += item.transfer_qty
                ps_source.save()

                # --- DESTINATION SIDE: ADD TO IN ---
                cs_dest, _ = CurrentStock.objects.select_for_update().get_or_create(
                    product=item.product, batch=item.batch,
                    location_type=instance.destination_type, location_id=instance.destination_id
                )
                cs_dest.in_qty += item.transfer_qty
                cs_dest.recompute_closing()

                ps_dest, _ = ProductStock.objects.select_for_update().get_or_create(
                    product=item.product, location_type=instance.destination_type, location_id=instance.destination_id
                )
                ps_dest.total_in_qty += item.transfer_qty
                ps_dest.save()
                # --- LEDGER ENTRIES ---
                # Ledger for Source (OUT)
                StockLedger.objects.create(
                    product=item.product, batch=item.batch,
                    location_type=instance.source_type, location_id=instance.source_id,
                    transaction_type='MTN_OUT', transaction_ref=f"MTN_ITEM_{item.id}",
                    document_id=instance.id, out_qty=item.transfer_qty,
                    balance_qty=cs_source.closing_qty, remarks=f"Transferred to {instance.destination_type}:{instance.destination_id}"
                )
                # Ledger for Destination (IN)
                StockLedger.objects.create(
                    product=item.product, batch=item.batch,
                    location_type=instance.destination_type, location_id=instance.destination_id,
                    transaction_type='MTN_IN', transaction_ref=f"MTN_ITEM_{item.id}",
                    document_id=instance.id, in_qty=item.transfer_qty,
                    balance_qty=cs_dest.closing_qty, remarks=f"Received from {instance.source_type}:{instance.source_id}"
                )





@receiver(post_delete, sender=MTNItem)
def handle_mtn_item_delete(sender, instance, **kwargs):
    mtn = instance.mtn

    if mtn.status != 'DRAFT':
        return

    qty = Decimal(instance.transfer_qty or 0)

    with transaction.atomic():
        cs = CurrentStock.objects.select_for_update().filter(
            product=instance.product,
            batch=instance.batch,
            location_type=mtn.source_type,
            location_id=mtn.source_id
        ).first()

        if cs:
            cs.reserved_qty -= qty
            if cs.reserved_qty < 0:
                cs.reserved_qty = Decimal('0')
            cs.recompute_closing()

        ps = ProductStock.objects.select_for_update().filter(
            product=instance.product,
            location_type=mtn.source_type,
            location_id=mtn.source_id
        ).first()

        if ps:
            ps.total_reserved_qty -= qty
            if ps.total_reserved_qty < 0:
                ps.total_reserved_qty = Decimal('0')
            ps.save()





@receiver(pre_save, sender=MaterialRequest)
def store_old_status(sender, instance, **kwargs):
    if instance.pk:
        old = MaterialRequest.objects.filter(pk=instance.pk).first()
        instance._old_status = old.status if old else None
    else:
        instance._old_status = None


# -------------------------------------------------
# On CREATE & STATUS CHANGE
# -------------------------------------------------
@receiver(post_save, sender=MaterialRequest)
def material_request_notification(sender, instance, created, **kwargs):

    # 🔔 1. When BRANCH creates request → Admin & HO
    if created and instance.status == "SUBMITTED":
        users = User.objects.filter(
            userprofile__role__in=["admin", "HO_manager"]
        )

        Notification.objects.bulk_create([
            Notification(
                user=u,
                title="New Material Request",
                message=f"Request {instance.request_no} raised by branch",
                related_request=instance
            ) for u in users
        ])

    # 🔔 2. When STATUS changes → Notify Branch
    elif not created and instance._old_status != instance.status:
        if instance.status in ["APPROVED", "REJECTED"]:

            branch_manager = User.objects.filter(
                username__in=BranchManager.objects.filter(
                    branch_id=instance.source_id
                ).values_list("mobile_no", flat=True)
            ).first()

            if branch_manager:
                Notification.objects.create(
                    user=branch_manager,
                    title=f"Material Request {instance.status}",
                    message=f"Your request {instance.request_no} was {instance.status.lower()}",
                    related_request=instance
                )