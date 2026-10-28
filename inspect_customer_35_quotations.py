from django.db import connection
from pprint import pprint

query = """
    SELECT
        q.id,
        q.quotation_no,
        q.quotation_date,
        q.customer_id,
        qs.product_id,
        q.product_details_json
    FROM crmapp_quotation_management q
    LEFT JOIN crmapp_quotation_management_selected_services qs
        ON qs.quotation_management_id = q.id
    WHERE q.customer_id = %s
    ORDER BY q.id, qs.product_id
"""

with connection.cursor() as cursor:
    cursor.execute(query, [35])
    rows = cursor.fetchall()

print("Rows found:", len(rows))
for row in rows:
    print("\nQuotation ID:", row[0])
    print("Quotation number:", row[1])
    print("Date:", row[2])
    print("Customer ID:", row[3])
    print("Selected product ID:", row[4])
    print("Product details JSON:")
    pprint(row[5])
