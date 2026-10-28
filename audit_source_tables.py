from django.apps import apps

for model in apps.get_app_config("crmapp").get_models():
    name = model.__name__.lower()
    if any(word in name for word in (
        "service", "invoice", "quotation", "customer", "product"
    )):
        try:
            print(f"{model.__name__}: {model.objects.count()} rows")
            print("  fields:", ", ".join(
                field.name for field in model._meta.fields
            ))
        except Exception as exc:
            print(f"{model.__name__}: count failed: {exc}")
