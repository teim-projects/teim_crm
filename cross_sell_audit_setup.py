from django.apps import apps

print("=== CUSTOMER MODELS ===")

for model in apps.get_models():
    if "customer" in model.__name__.lower() and model.__module__.startswith("crmapp"):
        try:
            print("\nMODEL:", model._meta.label)
            print("TOTAL RECORDS:", model.objects.count())
            print("FIELDS:", ", ".join(
                field.name for field in model._meta.get_fields()
            ))
        except Exception as exc:
            print("ERROR:", str(exc))

print("\n=== PRODUCT MODEL ===")

try:
    from crmapp.models import Product
    print("TOTAL PRODUCTS:", Product.objects.count())
    print("FIELDS:", ", ".join(
        field.name for field in Product._meta.get_fields()
    ))
except Exception as exc:
    print("PRODUCT INSPECTION ERROR:", str(exc))
