from crmapp.models import Product
from django.apps import apps

ids = [1, 54, 63]

print("=== PRODUCT USAGE ===")
for model in apps.get_models():
    for field in model._meta.fields:
        if getattr(field, "related_model", None) is Product:
            try:
                rows = model.objects.filter(
                    **{field.name + "__product_id__in": ids}
                ).values_list(field.name + "__product_id", flat=True)
                counts = {pid: 0 for pid in ids}
                for pid in rows:
                    if pid in counts:
                        counts[pid] += 1
                if any(counts.values()):
                    print(model.__name__, field.name, counts)
            except Exception:
                continue

print("\n=== PRODUCT CATALOG RECORDS ===")
for p in Product.objects.filter(product_id__in=ids).order_by("product_id"):
    print(p.product_id, p.product_name, p.category)
