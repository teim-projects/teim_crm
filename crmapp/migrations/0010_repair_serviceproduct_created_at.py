from django.db import migrations


def ensure_created_at_column(apps, schema_editor):
    table_name = "crmapp_serviceproduct"
    column_name = "created_at"

    with schema_editor.connection.cursor() as cursor:
        columns = {
            column.name.lower()
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        }

    if column_name not in columns:
        schema_editor.execute(
            "ALTER TABLE `crmapp_serviceproduct` "
            "ADD COLUMN `created_at` datetime(6) "
            "NOT NULL DEFAULT CURRENT_TIMESTAMP(6)"
        )


class Migration(migrations.Migration):

    dependencies = [
        ("crmapp", "0009_alter_product_hsn_code"),
    ]

    operations = [
        migrations.RunPython(
            ensure_created_at_column,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
