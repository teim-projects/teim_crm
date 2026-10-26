import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
django.setup()

from django.db import connection

customer_id = 6

with connection.cursor() as cursor:
    cursor.execute("SHOW COLUMNS FROM crmapp_product")
    product_columns = [row[0] for row in cursor.fetchall()]
    print("\nPRODUCT TABLE COLUMNS:")
    print(product_columns)

    cursor.execute("""
        SELECT id, customer_id, service_date, contract_type, contract_status
        FROM crmapp_service_management
        WHERE customer_id = %s
        ORDER BY id
    """, [customer_id])
    services = cursor.fetchall()

    print("\nSERVICE RECORDS:")
    for row in services:
        print(row)
    print("Total service records:", len(services))

    cursor.execute("""
        SELECT sp.id, sp.service_id, sp.product_id, sp.quantity,
               sp.price, p.*
        FROM crmapp_serviceproduct sp
        JOIN crmapp_service_management sm ON sm.id = sp.service_id
        JOIN crmapp_product p ON p.product_id = sp.product_id
        WHERE sm.customer_id = %s
        ORDER BY sp.service_id, sp.id
    """, [customer_id])
    product_rows = cursor.fetchall()

    print("\nSERVICE PRODUCT ROWS (including product details):")
    for row in product_rows:
        print(row)
    print("Total service-product rows:", len(product_rows))

    cursor.execute("""
        SELECT COUNT(*)
        FROM crmapp_quotation_management
        WHERE customer_id = %s
    """, [customer_id])
    print("\nQuotation count:", cursor.fetchone()[0])
