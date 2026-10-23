from django.apps import apps
from django.db import connection

names = [
    "customer_details",
    "Product",
    "service_management",
    "ServiceProduct",
    "quotation_management",
    "TaxInvoice",
    "TaxInvoiceItem",
    "AMCContract",
    "AMCServiceVisit",
]

with connection.cursor() as cursor:
    actual_tables = set(connection.introspection.table_names(cursor))

    for name in names:
        model = next(
            (m for m in apps.get_models()
             if m.__name__.lower() == name.lower()
             and m.__module__.startswith(("crmapp", "amc"))),
            None,
        )

        if model is None:
            print("\nNOT FOUND:", name)
            continue

        table = model._meta.db_table
        print(f"\n{'=' * 12} {model._meta.label} {'=' * 12}")
        print("TABLE:", table)

        if table not in actual_tables:
            print("TABLE MISSING FROM DATABASE")
            continue

        actual_columns = {
            col.name
            for col in connection.introspection.get_table_description(
                cursor, table
            )
        }
        expected_columns = {
            field.column for field in model._meta.local_concrete_fields
        }

        print("DATABASE ROW COUNT:", end=" ")
        cursor.execute(
            f"SELECT COUNT(*) FROM {connection.ops.quote_name(table)}"
        )
        print(cursor.fetchone()[0])

        print("ACTUAL DATABASE COLUMNS:", ", ".join(sorted(actual_columns)))
        print("MISSING EXPECTED COLUMNS:", 
              ", ".join(sorted(expected_columns - actual_columns)) or "None")
