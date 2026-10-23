from django.db import connection

queries = {
    "Total quotations": """
        SELECT COUNT(*) FROM crmapp_quotation_management
    """,
    "Unique customers with quotations": """
        SELECT COUNT(DISTINCT customer_id)
        FROM crmapp_quotation_management
        WHERE customer_id IS NOT NULL
    """,
    "Unique customers with selected products": """
        SELECT COUNT(DISTINCT q.customer_id)
        FROM crmapp_quotation_management q
        JOIN crmapp_quotation_management_selected_services s
          ON s.quotation_management_id = q.id
        WHERE q.customer_id IS NOT NULL
    """,
    "Unique products in quotations": """
        SELECT COUNT(DISTINCT product_id)
        FROM crmapp_quotation_management_selected_services
        WHERE product_id IS NOT NULL
    """,
    "Quotations without selected products": """
        SELECT COUNT(*)
        FROM crmapp_quotation_management q
        WHERE NOT EXISTS (
            SELECT 1
            FROM crmapp_quotation_management_selected_services s
            WHERE s.quotation_management_id = q.id
        )
    """,
    "Quotation rows with missing customer": """
        SELECT COUNT(*)
        FROM crmapp_quotation_management
        WHERE customer_id IS NULL
    """,
}

with connection.cursor() as cursor:
    print("\n=== SEVA QUOTATION COVERAGE AUDIT ===")
    for label, sql in queries.items():
        cursor.execute(sql)
        print(f"{label}: {cursor.fetchone()[0]}")
