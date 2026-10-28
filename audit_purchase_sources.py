from django.db import connection

queries = {
    "AMC VISIT STATUS": """
        SELECT allocation_status, has_complaint,
               COUNT(*) AS visits,
               COUNT(DISTINCT amc_id) AS contracts,
               COUNT(DISTINCT product_id) AS products
        FROM amc_amcservicevisit
        GROUP BY allocation_status, has_complaint
        ORDER BY visits DESC
    """,
    "AMC VISIT LINKAGE": """
        SELECT
            COUNT(*) AS total_visits,
            SUM(product_id IS NOT NULL) AS with_product,
            SUM(crm_service_id IS NOT NULL) AS linked_crm_service,
            SUM(complaint_service_id IS NOT NULL) AS linked_complaint,
            SUM(allocation_cancelled_reason IS NOT NULL
                AND allocation_cancelled_reason <> '') AS with_cancel_reason,
            COUNT(DISTINCT customer_id) AS customers
        FROM amc_amcservicevisit v
        JOIN amc_amccontract a ON a.id = v.amc_id
    """,
    "QUOTATION VERSION STATUS": """
        SELECT is_latest, COUNT(*) AS quotations,
               COUNT(DISTINCT customer_id) AS customers,
               COUNT(DISTINCT parent_quotation_id) AS parent_ids
        FROM crmapp_quotation_management
        GROUP BY is_latest
    """,
    "QUOTATION VERSION GROUPS": """
        SELECT COALESCE(parent_quotation_id, id) AS quotation_family,
               COUNT(*) AS versions,
               GROUP_CONCAT(CONCAT(id, ':v', version, ':latest=', is_latest)
                            ORDER BY version SEPARATOR ', ') AS details
        FROM crmapp_quotation_management
        GROUP BY COALESCE(parent_quotation_id, id)
        HAVING COUNT(*) > 1
        ORDER BY versions DESC
        LIMIT 15
    """,
    "INVOICE TO QUOTATION LINKAGE": """
        SELECT
            COUNT(*) AS invoices,
            SUM(quotation_id IS NOT NULL) AS linked_to_quotation,
            SUM(quotation_id IS NULL) AS without_quotation,
            COUNT(DISTINCT customer_id) AS customers,
            SUM(item_count) AS invoice_items
        FROM (
            SELECT i.id, i.customer_id, i.quotation_id,
                   COUNT(ii.id) AS item_count
            FROM crmapp_taxinvoice i
            LEFT JOIN crmapp_taxinvoiceitem ii
                ON ii.tax_invoice_id = i.id
            GROUP BY i.id, i.customer_id, i.quotation_id
        ) x
    """,
    "INVOICE QUOTATION CUSTOMER MATCH": """
        SELECT
            COUNT(*) AS linked_invoices,
            SUM(i.customer_id = q.customer_id) AS same_customer,
            SUM(i.customer_id <> q.customer_id) AS different_customer
        FROM crmapp_taxinvoice i
        JOIN crmapp_quotation_management q ON q.id = i.quotation_id
    """,
}

with connection.cursor() as cursor:
    for title, sql in queries.items():
        print(f"\n===== {title} =====")
        try:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            print(" | ".join(columns))
            for row in rows:
                print(" | ".join(str(value) for value in row))
            if not rows:
                print("(no rows)")
        except Exception as exc:
            print(f"Query failed: {exc}")
