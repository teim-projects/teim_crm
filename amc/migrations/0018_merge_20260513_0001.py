# Manual merge migration: resolves the conflict between kunal-seva branch
# (0017_amcservicevisit_auto_allocation_done which adds auto_allocation_done)
# and bharat-new branch (0006_remove_amcservicevisit_auto_allocation_done_and_more
# which removes auto_allocation_done).
# Since both are already applied in the DB, this migration is a no-op merge point.
# The actual DB state already reflects all operations from both branches.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('amc', '0006_remove_amcservicevisit_auto_allocation_done_and_more'),
        ('amc', '0017_amcservicevisit_auto_allocation_done'),
    ]

    operations = [
        # No operations needed — both branches have been applied to DB already.
        # This migration just unifies the two leaf nodes in the migration graph.
    ]
