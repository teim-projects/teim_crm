import django.shortcuts
import crmapp.views as views
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser

original_render = django.shortcuts.render
captured = {}

def capture_render(request, template_name, context=None, *args, **kwargs):
    captured["template"] = template_name
    captured["context"] = context or {}
    return original_render(request, template_name, context, *args, **kwargs)

django.shortcuts.render = capture_render
factory = RequestFactory()

try:
    for customer_id in (85, 16, 1):
        captured.clear()
        print(f"\n===== CUSTOMER {customer_id} =====")

        request = factory.post(
            "/product-recommendations/",
            {"customer_id": str(customer_id), "mode": "CROSS_SELL"},
        )
        request.user = AnonymousUser()

        try:
            response = views.product_recommendations(request)
            context = captured.get("context", {})

            print("HTTP:", response.status_code)
            print("Template:", captured.get("template"))
            print("Selected customer:", getattr(context.get("selected_customer"), "id", None))
            print("Purchase history:", len(context.get("purchase_history") or []))
            print("Recommendations:", len(context.get("recommendations") or []))
            print("Error:", context.get("error_message"))

        except Exception as exc:
            print("ERROR:", type(exc).__name__, str(exc))
finally:
    django.shortcuts.render = original_render
