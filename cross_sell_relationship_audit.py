from django.db import connection

tables = [
    "crmapp_customer_details",
    "crmapp_product",
    "crmapp_service_management",
    "crmapp_serviceproduct",
    "crmapp_quotation_management",
    "crmapp_taxinvoice",
    "crmapp_taxinvoiceitem",
    "amc_amccontract",
    "amc_amcservicevisit",
]

with connection.cursor() as cursor:
    print("\n=== ACTUAL FOREIGN-KEY RELATIONSHIPS ===")
    cursor.execute("""
        SELECT TABLE_NAME, COLUMN_NAME,
               REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA = DATABASE()
          AND REFERENCED_TABLE_NAME IS NOT NULL
          AND TABLE_NAME IN (
              'crmapp_customer_details',
              'crmapp_product',
              'crmapp_service_management',
              'crmapp_serviceproduct',
              'crmapp_quotation_management',
              'crmapp_taxinvoice',
              'crmapp_taxinvoiceitem',
              'amc_amccontract',
              'amc_amcservicevisit'
          )
        ORDER BY TABLE_NAME, COLUMN_NAME
    """)
    for row in cursor.fetchall():
        print(row)

    samples = {
        "crmapp_service_management":
            "id, customer_id, service_subject, service_date",
        "crmapp_serviceproduct":
            "id, service_id, product_id, description, quantity",
        "crmapp_quotation_management":
            "id, customer_id, quotation_no, product_details_json",
        "crmapp_taxinvoiceitem":
            "id, tax_invoice_id, product_name, quantity",
        "amc_amccontract":
            "id, customer_id, service_id, service_description",
        "amc_amcservicevisit":
            "id, amc_id, crm_service_id, product_id, service_date",
    }

    print("\n=== SAMPLE SERVICE / PRODUCT HISTORY ===")
    for table, columns in samples.items():
        print(f"\n--- {table} ---")
        cursor.execute(f"SELECT {columns} FROM `{table}` LIMIT 5")
        for row in cursor.fetchall():
            print(tuple(
                str(value)[:180] if value is not None else None
                for value in row
            ))
