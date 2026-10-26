from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.loader import MigrationLoader

branch_table = apps.get_model("crmapp", "Branch")._meta.db_table
user_table = get_user_model()._meta.db_table
tables = set(connection.introspection.table_names())

missing_dependencies = [
    t for t in [branch_table, user_table] if t not in tables
]

if missing_dependencies:
    print("STOP: Required tables are missing:", missing_dependencies)
else:
    loader = MigrationLoader(connection)
    state = loader.project_state([
        ("crmapp", "0002_serviceproductfrequency_duration_months")
    ])
    historical_operation = state.apps.get_model(
        "crmapp", "OperationPerson"
    )

    models_to_check = [
        apps.get_model("crmapp", "BranchManager"),
        apps.get_model("crmapp", "OperationPerson"),
        apps.get_model("crmapp", "SalesPerson"),
        apps.get_model("crmapp", "TechnicianProfile"),
    ]

    with connection.schema_editor() as editor:
        tables = set(connection.introspection.table_names())

        operation_table = historical_operation._meta.db_table
        if operation_table not in tables:
            editor.create_model(historical_operation)
            print("Created missing table:", operation_table)

        for model in models_to_check:
            table = model._meta.db_table
            if table not in connection.introspection.table_names():
                print("STOP: Model table is still missing:", table)
                break

            with connection.cursor() as cursor:
                columns = {
                    c.name for c in
                    connection.introspection.get_table_description(cursor, table)
                }

            if "is_active" not in columns:
                editor.add_field(model, model._meta.get_field("is_active"))
                print("Added is_active to:", table)
            else:
                print("Already exists:", table, "is_active")

    print("Repair script finished. Verify before proceeding.")
