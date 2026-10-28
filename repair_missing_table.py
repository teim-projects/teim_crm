from django.db import connection
from django.db.migrations.loader import MigrationLoader

loader = MigrationLoader(connection)
state = loader.project_state([("crmapp", "0001_initial")])
model = state.apps.get_model("crmapp", "ServiceProductFrequency")

with connection.schema_editor() as editor:
    editor.create_model(model)

print("Missing table created using the original migration definition.")
