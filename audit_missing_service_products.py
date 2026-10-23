import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT
            sm.customer_id,
            cd.customerid,
            cd.fullname,
            sm.id AS service_id,
            sm.service_date,
            COUNT(sp.id) AS linked_products
        FROM crmapp_service_management sm
        LEFT JOIN crmapp_serviceproduct sp
            ON sp.service_id = sm.id
        LEFT JOIN crmapp_customer_details cd
            ON cd.id = sm.customer_id
        WHERE sm.customer_id IS NOT NULL
        GROUP BY
            sm.customer_id, cd.customerid, cd.fullname,
            sm.id, sm.service_date
        HAVING COUNT(sp.id) = 0
        ORDER BY sm.customer_id, sm.id
    """)
    rows = cursor.fetchall()

    print("\n=== SERVICES WITH NO LINKED PRODUCTS ===")
    for row in rows:
        print(row)

    print("\nTotal services without linked products:", len(rows))
    print(
        "Distinct customers affected:",
        len({row[0] for row in rows})
    )

    cursor.execute("""
        SELECT
            COUNT(DISTINCT sm.id),
            COUNT(DISTINCT sp.id),
            COUNT(DISTINCT sm.customer_id)
        FROM crmapp_service_management sm
        LEFT JOIN crmapp_serviceproduct sp
            ON sp.service_id = sm.id
    """)
    print("\nOverall totals (services, linked product rows, customers):")
    print(cursor.fetchone())
