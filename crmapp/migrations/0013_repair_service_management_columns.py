from django.db import migrations


def ensure_service_management_columns(apps, schema_editor):
    table = "crmapp_service_management"
    required_columns = {
        "branch_id": "BIGINT NULL",
        "latitude": "DOUBLE NULL",
        "longitude": "DOUBLE NULL",
        "sales_person_email": "VARCHAR(254) NULL",
    }

    with schema_editor.connection.cursor() as cursor:
        columns = {
            c.name.lower()
            for c in schema_editor.connection.introspection.get_table_description(
                cursor, table
            )
        }

    for column, definition in required_columns.items():
        if column not in columns:
            schema_editor.execute(
                f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}"
            )
            columns.add(column)


class Migration(migrations.Migration):
    dependencies = [
        ("crmapp", "0012_repair_service_is_approved"),
    ]

    operations = [
        migrations.RunPython(
            ensure_service_management_columns,
            migrations.RunPython.noop,
        ),
    ]
