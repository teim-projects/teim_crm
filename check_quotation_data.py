from django.db import connection

tables = [
    "crmapp_quotation_management",
    "crmapp_quotation_management_selected_services",
]

with connection.cursor() as cursor:
    for table in tables:
        print("\nTABLE:", table)
        try:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            print("COLUMNS:", [row[0] for row in cursor.fetchall()])

            cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
            print("ROWS:", cursor.fetchone()[0])
        except Exception as error:
            print("ERROR:", error)
