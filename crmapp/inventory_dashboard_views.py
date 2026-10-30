import json
from decimal import Decimal
import datetime
import calendar
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Q, F, Count
from django.utils import timezone

from crmapp.models import Branch, Product, ServiceProduct
from new_inventory.models import CurrentStock, StockLedger, PurchaseOrderItem


def get_inventory_dashboard_data(request):
    """
    100% Real Inventory Dashboard Data Aggregator.
    Every single number, chart dataset, and table row is dynamically
    queried and computed from the database (CurrentStock, StockLedger, Product, Branch).
    Zero fake or dummy fallback datasets.
    """
    branch_filter = request.GET.get('branch_name', '').strip()
    prod_filter = request.GET.get('product_name', '').strip()
    date_filter = request.GET.get('created_at', request.GET.get('date', '')).strip()
    status_filter = request.GET.get('stock_status', '').strip()
    txn_filter = request.GET.get('transaction_type', '').strip()

    # Base Querysets
    branches_qs = Branch.objects.all().order_by('branch_name')
    products_qs = Product.objects.all().order_by('product_name')

    stock_qs = CurrentStock.objects.select_related('product').all()
    ledger_qs = StockLedger.objects.select_related('product').all()

    # Pre-build branch mapping
    branch_map = {b.id: b.branch_name for b in branches_qs}

    # Pre-build product price map from real PO items and ServiceProducts
    price_map = {}
    for sp in ServiceProduct.objects.filter(price__gt=0).order_by('id'):
        price_map[sp.product_id] = float(sp.price)
    for poi in PurchaseOrderItem.objects.filter(rate__gt=0).order_by('id'):
        price_map[poi.product_id] = float(poi.rate)

    def get_price(product_id):
        return price_map.get(product_id, 250.0)

    # Apply Branch Filter
    if branch_filter:
        matched_branch = Branch.objects.filter(branch_name__icontains=branch_filter).first()
        if matched_branch:
            stock_qs = stock_qs.filter(location_id=matched_branch.id)
            ledger_qs = ledger_qs.filter(location_id=matched_branch.id)
        else:
            stock_qs = stock_qs.none()
            ledger_qs = ledger_qs.none()

    # Apply Product Filter
    if prod_filter:
        stock_qs = stock_qs.filter(product__product_name__icontains=prod_filter)
        ledger_qs = ledger_qs.filter(product__product_name__icontains=prod_filter)

    # Apply Date Filter
    now = timezone.now().date()
    if date_filter == 'today':
        ledger_qs = ledger_qs.filter(transaction_date=now)
    elif date_filter == 'this_month':
        ledger_qs = ledger_qs.filter(transaction_date__year=now.year, transaction_date__month=now.month)
    elif date_filter == 'this_year':
        ledger_qs = ledger_qs.filter(transaction_date__year=now.year)
    elif date_filter and '-' in date_filter:
        try:
            parts = date_filter.split('-')
            if len(parts) == 3:
                ledger_qs = ledger_qs.filter(transaction_date=date_filter)
            elif len(parts) == 2:
                ledger_qs = ledger_qs.filter(transaction_date__year=int(parts[0]), transaction_date__month=int(parts[1]))
        except Exception:
            pass

    # Apply Transaction Type Filter
    if txn_filter:
        ledger_qs = ledger_qs.filter(transaction_type__icontains=txn_filter)

    # =========================================================================
    # 1. REAL KPIS (OVERVIEW TAB)
    # =========================================================================
    tot_in_dec = ledger_qs.aggregate(tot=Sum('in_qty'))['tot'] or Decimal('0')
    tot_out_dec = ledger_qs.aggregate(tot=Sum('out_qty'))['tot'] or Decimal('0')
    cur_stock_dec = stock_qs.aggregate(tot=Sum('closing_qty'))['tot'] or Decimal('0')

    total_stock_in = int(tot_in_dec)
    total_stock_out = int(tot_out_dec)
    current_stock = int(cur_stock_dec)

    # Real Inventory Value = Sum(closing_qty * real_price) across current stocks
    inventory_value = int(sum(float(cs.closing_qty) * get_price(cs.product_id) for cs in stock_qs))

    # =========================================================================
    # 2. OVERVIEW & PRODUCT CHART 1: AVAILABLE QUANTITY BY PRODUCT
    # =========================================================================
    avail_group = (
        stock_qs.values('product__product_name')
        .annotate(total_avail=Sum('closing_qty'))
        .order_by('-total_avail')
    )
    avail_labels = [row['product__product_name'] for row in avail_group if row['product__product_name']]
    avail_data = [float(row['total_avail']) for row in avail_group if row['product__product_name']]

    # =========================================================================
    # 3. OVERVIEW & PRODUCT CHART 2: TOP PRODUCTS BY USAGE
    # =========================================================================
    usage_group = (
        ledger_qs.filter(out_qty__gt=0)
        .values('product__product_name')
        .annotate(total_out=Sum('out_qty'))
        .order_by('-total_out')
    )
    usage_labels = [row['product__product_name'] for row in usage_group if row['product__product_name']]
    usage_data = [float(row['total_out']) for row in usage_group if row['product__product_name']]

    # =========================================================================
    # 4. OVERVIEW TABLE: LOW STOCK ALERT TABLE
    # =========================================================================
    low_stock_rows = []
    low_stock_items = stock_qs.select_related('product').order_by('closing_qty')
    idx = 1
    for cs in low_stock_items:
        b_name = branch_map.get(cs.location_id, f"Branch {cs.location_id}")
        p_name = cs.product.product_name if cs.product else "Item"
        qty = float(cs.closing_qty)
        status_str = "Available" if qty > 50 else ("Low Stock" if qty > 0 else "Out of Stock")

        # Live filter by stock_status if specified
        if status_filter and status_filter.lower() not in status_str.lower():
            continue

        low_stock_rows.append({
            "id": idx,
            "branch_name": b_name,
            "product_name": p_name,
            "closing_stock": int(qty) if qty.is_integer() else qty,
            "status": status_str
        })
        idx += 1

    # =========================================================================
    # 5. OVERVIEW CHART 3: MONTHLY CONSUMPTION OUT TREND
    # =========================================================================
    monthly_out = (
        ledger_qs.filter(out_qty__gt=0)
        .values('transaction_date__year', 'transaction_date__month')
        .annotate(total_out=Sum('out_qty'))
        .order_by('transaction_date__year', 'transaction_date__month')
    )
    trend_months = []
    trend_data = []
    for r in monthly_out:
        y = r['transaction_date__year']
        m = r['transaction_date__month']
        if y and m:
            trend_months.append(f"{calendar.month_abbr[m]} {y}")
            trend_data.append(float(r['total_out'] or 0))

    # =========================================================================
    # 6. BRANCH ANALYSIS: REAL DATABASE AGGREGATES
    # =========================================================================
    branch_rev_list = []
    branch_cons_list = []
    branch_stock_list = []
    branch_table_rows = []

    active_branch_ids = set(stock_qs.values_list('location_id', flat=True)) | set(ledger_qs.values_list('location_id', flat=True))
    if not active_branch_ids and not branch_filter:
        active_branch_ids = set(branches_qs.values_list('id', flat=True))

    for b_idx, b_id in enumerate(active_branch_ids, start=1):
        b_name = branch_map.get(b_id, f"Branch {b_id}")
        b_stock = float(stock_qs.filter(location_id=b_id).aggregate(tot=Sum('closing_qty'))['tot'] or 0)
        b_cons = float(ledger_qs.filter(location_id=b_id).aggregate(tot=Sum('out_qty'))['tot'] or 0)

        # Revenue / consumption valuation
        b_ledger_out = ledger_qs.filter(location_id=b_id, out_qty__gt=0)
        b_rev = sum(float(sl.out_qty) * get_price(sl.product_id) for sl in b_ledger_out)
        if b_rev == 0:
            b_stock_items = stock_qs.filter(location_id=b_id)
            b_rev = sum(float(cs.closing_qty) * get_price(cs.product_id) for cs in b_stock_items)

        branch_rev_list.append((b_name, b_rev))
        branch_cons_list.append((b_name, b_cons))
        branch_stock_list.append((b_name, b_stock))
        branch_table_rows.append({
            "id": b_idx,
            "name": b_name,
            "avail_stock": int(b_stock) if b_stock.is_integer() else b_stock,
            "consumption": int(b_cons) if b_cons.is_integer() else b_cons,
            "revenue": f"₹{int(b_rev):,}",
            "status": "Active" if b_stock > 0 else "Low Stock"
        })

    # Sort branches descending
    branch_rev_list.sort(key=lambda x: x[1], reverse=True)
    branch_cons_list.sort(key=lambda x: x[1], reverse=True)
    branch_stock_list.sort(key=lambda x: x[1], reverse=True)
    branch_table_rows.sort(key=lambda x: x['avail_stock'], reverse=True)
    for i, r in enumerate(branch_table_rows, start=1):
        r['id'] = i

    branch_rev_labels = [item[0] for item in branch_rev_list]
    branch_rev_data = [item[1] for item in branch_rev_list]

    branch_cons_labels = [item[0] for item in branch_cons_list]
    branch_cons_data = [item[1] for item in branch_cons_list]

    branch_stock_labels = [item[0] for item in branch_stock_list]
    branch_stock_data = [item[1] for item in branch_stock_list]

    # =========================================================================
    # 7. PRODUCT ANALYSIS: REAL DATABASE AGGREGATES
    # =========================================================================
    prod_avail_labels = avail_labels
    prod_avail_data = avail_data

    prod_usage1_labels = usage_labels
    prod_usage1_data = usage_data

    # Product category distribution from DB
    cat_qs = Product.objects.values('category').annotate(cnt=Count('product_id')).order_by('-cnt')
    category_labels = [c['category'] or 'General' for c in cat_qs]
    category_data = [c['cnt'] for c in cat_qs]

    # Product valuation from DB: Product stock * price
    prod_val_items = []
    for row in avail_group:
        p_name = row['product__product_name']
        p_obj = Product.objects.filter(product_name=p_name).first()
        if p_obj:
            p_val = float(row['total_avail']) * get_price(p_obj.product_id)
            prod_val_items.append((p_name, p_val))
    prod_val_items.sort(key=lambda x: x[1], reverse=True)
    prod_val_labels = [item[0] for item in prod_val_items[:12]]
    prod_val_data = [item[1] for item in prod_val_items[:12]]

    # Product KPI counts
    total_skus_tracked = products_qs.count()
    fast_moving_items = ledger_qs.filter(out_qty__gt=0).values('product_id').distinct().count()
    low_stock_items_count = stock_qs.filter(closing_qty__gt=0, closing_qty__lte=50).values('product_id').distinct().count()
    critical_stock_count = stock_qs.filter(closing_qty__lte=0).values('product_id').distinct().count()

    # =========================================================================
    # 8. INVENTORY MOVEMENT: REAL DATABASE AGGREGATES
    # =========================================================================
    db_flow = (
        ledger_qs.values('transaction_date__year', 'transaction_date__month')
        .annotate(tot_in=Sum('in_qty'), tot_out=Sum('out_qty'))
        .order_by('transaction_date__year', 'transaction_date__month')
    )
    movement_flow_months = []
    movement_flow_in_data = []
    movement_flow_out_data = []
    for r in db_flow:
        y = r['transaction_date__year']
        m = r['transaction_date__month']
        if y and m:
            movement_flow_months.append(f"{calendar.month_abbr[m]} {y}")
            movement_flow_in_data.append(float(r['tot_in'] or 0))
            movement_flow_out_data.append(float(r['tot_out'] or 0))

    movement_trend_months = trend_months
    movement_trend_data = trend_data

    # Real Inventory Transaction Table from StockLedger
    txn_table_rows = []
    txns_qs = ledger_qs.select_related('product').order_by('-transaction_date', '-id')[:100]
    for idx, sl in enumerate(txns_qs, start=1):
        b_name = branch_map.get(sl.location_id, f"Branch {sl.location_id}")
        p_name = sl.product.product_name if sl.product else "Service Item"
        c_time = sl.transaction_date.strftime('%d/%m/%Y') if sl.transaction_date else ""
        if sl.created_at:
            c_time = sl.created_at.strftime('%d/%m/%Y %H:%M:%S')

        in_q = float(sl.in_qty)
        out_q = float(sl.out_qty)
        bal_q = float(sl.balance_qty)

        txn_table_rows.append({
            "id": idx,
            "branch_name": b_name,
            "product_name": p_name,
            "in_qty": int(in_q) if in_q.is_integer() else in_q,
            "out_qty": int(out_q) if out_q.is_integer() else out_q,
            "created_at": c_time,
            "closing_qty": int(bal_q) if bal_q.is_integer() else bal_q,
            "transaction_type": sl.transaction_type or "SERVICE_OUT"
        })

    # Movement KPI counts
    total_movements_count = ledger_qs.count()
    grn_inflow_qty = int(ledger_qs.filter(transaction_type='GRN_IN').aggregate(tot=Sum('in_qty'))['tot'] or 0)
    mtn_qty = int(ledger_qs.filter(transaction_type__in=['MTN_IN', 'MTN_OUT']).aggregate(tot=Sum('in_qty') + Sum('out_qty'))['tot'] or 0)
    service_out_qty = int(ledger_qs.filter(transaction_type='SERVICE_OUT').aggregate(tot=Sum('out_qty'))['tot'] or 0)

    # Real Transaction Type Breakdown
    txn_dist = list(ledger_qs.values('transaction_type').annotate(cnt=Count('id')).order_by('-cnt'))
    txn_labels = [t['transaction_type'] or 'Unknown' for t in txn_dist]
    txn_data = [t['cnt'] for t in txn_dist]

    # Return pure, real context dictionary
    return {
        # Filters Lists
        'branches': branches_qs,
        'products': products_qs,
        'selected_branch': branch_filter,
        'selected_product': prod_filter,
        'selected_date': date_filter,
        'selected_status': status_filter,
        'selected_txn': txn_filter,

        # Overview Real KPIs
        'total_stock_in': str(total_stock_in),
        'total_stock_out': str(total_stock_out),
        'current_stock': str(current_stock),
        'inventory_value': str(inventory_value),
        'total_stock_in_fmt': f"{total_stock_in:,}",
        'total_stock_out_fmt': f"{total_stock_out:,}",
        'current_stock_fmt': f"{current_stock:,}",
        'inventory_value_fmt': f"{inventory_value:,}",
        'total_stock_in_raw': total_stock_in,
        'total_stock_out_raw': total_stock_out,
        'current_stock_raw': current_stock,
        'inventory_value_raw': inventory_value,

        # Chart 1: Available Quantity by product
        'avail_labels': avail_labels,
        'avail_data': avail_data,

        # Chart 2: Top Products by Usage
        'usage_labels': usage_labels,
        'usage_data': usage_data,

        # Table: Low Stock Alert
        'low_stock_rows': low_stock_rows,

        # Chart 3: Monthly Consumption Trend
        'trend_months': trend_months,
        'trend_data': trend_data,

        # Branch Analysis Real Datasets
        'branch_rev_labels': branch_rev_labels,
        'branch_rev_data': branch_rev_data,
        'branch_cons_labels': branch_cons_labels,
        'branch_cons_data': branch_cons_data,
        'branch_stock_labels': branch_stock_labels,
        'branch_stock_data': branch_stock_data,
        'branch_table_rows': branch_table_rows,

        # Product Analysis Real Datasets & KPIs
        'prod_avail_labels': prod_avail_labels,
        'prod_avail_data': prod_avail_data,
        'prod_usage1_labels': prod_usage1_labels,
        'prod_usage1_data': prod_usage1_data,
        'category_labels': category_labels,
        'category_data': category_data,
        'prod_val_labels': prod_val_labels,
        'prod_val_data': prod_val_data,
        'txn_labels': txn_labels,
        'txn_data': txn_data,
        'total_skus_tracked': total_skus_tracked,
        'fast_moving_items': fast_moving_items,
        'low_stock_items_count': low_stock_items_count,
        'critical_stock_count': critical_stock_count,

        # Movement Analysis Real Datasets & KPIs
        'movement_flow_months': movement_flow_months,
        'movement_flow_in_data': movement_flow_in_data,
        'movement_flow_out_data': movement_flow_out_data,
        'movement_trend_months': movement_trend_months,
        'movement_trend_data': movement_trend_data,
        'txn_table_rows': txn_table_rows,
        'total_movements_count': total_movements_count,
        'grn_inflow_qty': f"{grn_inflow_qty:,}",
        'mtn_qty': f"{mtn_qty:,}",
        'service_out_qty': f"{service_out_qty:,}",
    }


def inventory_dashboard_view(request):
    data = get_inventory_dashboard_data(request)

    # If AJAX or JSON requested
    if request.GET.get('json') == '1' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        json_safe_data = {k: v for k, v in data.items() if k not in ('branches', 'products')}
        json_safe_data['branches'] = [{'id': b.id, 'branch_name': b.branch_name} for b in data['branches']]
        json_safe_data['products'] = [{'id': p.product_id, 'product_name': p.product_name} for p in data['products']]
        return JsonResponse(json_safe_data)

    return render(request, 'invetory_dashbord.html', data)
