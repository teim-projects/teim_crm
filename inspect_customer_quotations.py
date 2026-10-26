from django.db import connection

query = """
    SELECT
        q.id,
        q.quotation_no,
        q.version,
        q.is_latest,
        q.parent_quotation_id,
        qs.product_id,
        p.product_name
    FROM crmapp_quotation_management q
    LEFT JOIN crmapp_quotation_management_selected_services qs
        ON qs.quotation_management_id = q.id
    LEFT JOIN crmapp_product p
        ON p.product_id = qs.product_id
    WHERE q.customer_id = %s
    ORDER BY q.quotation_no, q.version, q.id, qs.product_id
"""

with connection.cursor() as cursor:
    cursor.execute(query, [35])
    rows = cursor.fetchall()

print("Quotation rows for Customer 35:", len(rows))
for row in rows:
    print(row)
