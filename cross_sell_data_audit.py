from django.apps import apps

models_to_check = [
    "customer_details",
    "Product",
    "service_management",
    "ServiceProduct",
    "quotation_management",
    "TaxInvoice",
    "TaxInvoiceItem",
    "AMCContract",
    "AMCServiceVisit",
]

for name in models_to_check:
    model = next(
        (m for m in apps.get_models()
         if m.__name__.lower() == name.lower()
         and m.__module__.startswith(("crmapp", "amc"))),
        None,
    )

    if not model:
        print("\nMODEL NOT FOUND:", name)
        continue

    print(f"\n{'=' * 18} {model._meta.label} {'=' * 18}")
    print("COUNT:", model.objects.count())
    print("FIELDS:")

    for field in model._meta.get_fields():
        if not getattr(field, "concrete", False):
            continue
        related = getattr(field, "related_model", None)
        print(
            f"  {field.name} ({field.get_internal_type()})"
            + (f" -> {related._meta.label}" if related else "")
        )

    print("SAMPLE RECORDS (maximum 3):")
    for obj in model.objects.all()[:3]:
        row = {}
        for field in model._meta.concrete_fields:
            if field.is_relation:
                row[field.name + "_id"] = getattr(obj, field.attname, None)
            elif any(word in field.name.lower() for word in [
                "email", "phone", "contact", "address", "signature"
            ]):
                continue
            else:
                value = getattr(obj, field.attname, None)
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                row[field.name] = value
        print(row)
