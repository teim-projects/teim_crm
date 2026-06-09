from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum

from .models import (
    CurrentStock,
    MonthlyStockSnapshot,
    StockLedger
)


def auto_month_snapshot():

    today = timezone.now()

    year = today.year
    month = today.month

    stocks = CurrentStock.objects.all()

    for stock in stocks:

        exists = MonthlyStockSnapshot.objects.filter(
            product=stock.product,
            location_type=stock.location_type,
            location_id=stock.location_id,
            year=year,
            month=month
        ).exists()

        if exists:
            continue

        prev_month = month - 1
        prev_year = year

        if prev_month == 0:
            prev_month = 12
            prev_year -= 1

        previous = MonthlyStockSnapshot.objects.filter(
            product=stock.product,
            location_type=stock.location_type,
            location_id=stock.location_id,
            year=prev_year,
            month=prev_month
        ).first()

        # Opening = Previous Month Closing
        opening = (
            previous.closing_qty
            if previous
            else Decimal("0.000")
        )

        # Receipt
        receipt = stock.in_qty or Decimal("0.000")

        # Sent
        sent = stock.out_qty or Decimal("0.000")

        # Approved Qty
        approved = (
            StockLedger.objects.filter(
                product=stock.product,
                location_type=stock.location_type,
                location_id=stock.location_id,
                transaction_type="SERVICE_OUT"
            )
            .aggregate(total=Sum("out_qty"))
            .get("total")
            or Decimal("0.000")
        )

        # Closing Formula
        closing = max(
            Decimal("0.000"),
            opening + receipt - sent - approved
        )

        MonthlyStockSnapshot.objects.create(
            product=stock.product,
            location_type=stock.location_type,
            location_id=stock.location_id,

            year=year,
            month=month,

            opening_qty=opening,
            receipt_qty=receipt,
            sent_qty=sent,
            approved_qty=approved,
            closing_qty=closing
        )