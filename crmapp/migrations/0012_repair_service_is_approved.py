from django.db import migrations


def ensure_is_approved(apps, schema_editor):
    table = "crmapp_service_management"
    with schema_editor.connection.cursor() as cursor:
        columns = {
            c.name.lower()
            for c in schema_editor.connection.introspection.get_table_description(
                cursor, table
            )
        }

    if "is_approved" not in columns:
        schema_editor.execute(
            "ALTER TABLE `crmapp_service_management` "
            "ADD COLUMN `is_approved` bool NOT NULL DEFAULT 0"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("crmapp", "0011_repair_customer_branch_id"),
    ]

    operations = [
        migrations.RunPython(ensure_is_approved, migrations.RunPython.noop),
    ]
