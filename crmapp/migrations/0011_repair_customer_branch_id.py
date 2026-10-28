from django.db import migrations


def ensure_branch_id(apps, schema_editor):
    table = "crmapp_customer_details"
    with schema_editor.connection.cursor() as cursor:
        columns = {
            c.name.lower()
            for c in schema_editor.connection.introspection.get_table_description(
                cursor, table
            )
        }

    if "branch_id" not in columns:
        schema_editor.execute(
            "ALTER TABLE `crmapp_customer_details` "
            "ADD COLUMN `branch_id` bigint NULL"
        )

    with schema_editor.connection.cursor() as cursor:
        constraints = schema_editor.connection.introspection.get_constraints(
            cursor, table
        )

    has_branch_fk = any(
        details.get("foreign_key")
        and details.get("columns") == ["branch_id"]
        and details["foreign_key"][0].lower() == "crmapp_branch"
        for details in constraints.values()
    )

    if not has_branch_fk:
        schema_editor.execute(
            "ALTER TABLE `crmapp_customer_details` "
            "ADD CONSTRAINT `customer_details_branch_id_fk` "
            "FOREIGN KEY (`branch_id`) REFERENCES `crmapp_branch` (`id`) "
            "ON DELETE SET NULL"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("crmapp", "0010_repair_serviceproduct_created_at"),
    ]

    operations = [
        migrations.RunPython(ensure_branch_id, migrations.RunPython.noop),
    ]
