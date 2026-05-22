"""
kunal darekar - Manual migration: create crmapp_serviceproductfrequency table.
The table was defined in 0001_initial but never actually applied to the DB
because of a broken migration graph (amc 0009 references a non-existent
field which blocks `migrate` from loading the full project state).

We use RunSQL so this works even if makemigrations cannot build the graph.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('crmapp', '0016_merge_20260513_0001'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS `crmapp_serviceproductfrequency` (
                `id`         BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                `frequency`  INT NOT NULL,
                `remarks`    VARCHAR(255) NULL,
                `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                `product_id` INT NOT NULL,
                `service_id` BIGINT NOT NULL,
                CONSTRAINT `crmapp_spfreq_product_fk`
                    FOREIGN KEY (`product_id`)
                    REFERENCES `crmapp_product` (`product_id`)
                    ON DELETE CASCADE,
                CONSTRAINT `crmapp_spfreq_service_fk`
                    FOREIGN KEY (`service_id`)
                    REFERENCES `crmapp_service_management` (`id`)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
            reverse_sql="DROP TABLE IF EXISTS `crmapp_serviceproductfrequency`;",
        ),
    ]
