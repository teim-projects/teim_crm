from django.apps import apps

print("=== MODELS CONNECTED TO CUSTOMERS OR PRODUCTS ===")

for model in apps.get_models():
    try:
        relevant = []

        for field in model._meta.get_fields():
            related_model = getattr(field, "related_model", None)
            target = related_model._meta.label if related_model else ""

            if (
                "customer_details" in target.lower()
                or target == "crmapp.Product"
                or any(word in field.name.lower()
                       for word in ["customer", "product", "quotation", "invoice", "service"])
            ):
                relevant.append(
                    f"{field.name} -> {target or 'scalar field'}"
                )

        if relevant:
            print(f"\nMODEL: {model._meta.label}")
            try:
                print("RECORDS:", model.objects.count())
            except Exception:
                print("RECORDS: unavailable")
            for item in relevant:
                print(" ", item)

    except Exception as exc:
        print("INSPECTION ERROR:", model.__name__, str(exc))
