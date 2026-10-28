from django.db import connection

tables = [
    "amc_amcservicevisit",
    "amc_amccontract",
    "crmapp_quotation_management",
    "crmapp_quotation_management_selected_services",
    "crmapp_taxinvoice",
    "crmapp_taxinvoiceitem",
]

with connection.cursor() as cursor:
    existing = set(connection.introspection.table_names())
    for table in tables:
        print(f"\n===== {table} =====")
        if table not in existing:
            print("Table not found")
            continue
        for column in connection.introspection.get_table_description(cursor, table):
            print(column.name, column.type_code)
