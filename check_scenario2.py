from django.test import Client
from crmapp.models import customer_details, ServiceProduct

client = Client(HTTP_HOST="localhost")
checked = passed = 0
failed = []

for c in customer_details.objects.only("id", "fullname").iterator():
    if not ServiceProduct.objects.filter(service__customer_id=c.id).exists():
        continue

    checked += 1
    r = client.post("/product-recommendations/", {
        "customer_id": str(c.id),
        "mode": "CROSS_SELL",
    })

    if r.status_code != 200:
        failed.append((c.id, f"HTTP {r.status_code}"))
        continue

    html = r.content.decode("utf-8", errors="replace")
    if "Could not generate recommendations:" in html:
        failed.append((c.id, "Recommendation error shown"))
    elif (
        "Purchase history found, but no eligible cross-sell recommendations" in html
        or "recommendation(s) returned" in html
    ):
        passed += 1
    else:
        failed.append((c.id, "Neither results nor expected empty state found"))

print(f"Scenario 2 checked: {checked}")
print(f"Passed: {passed}")
print(f"Failed: {len(failed)}")
for item in failed:
    print("FAILED:", item)

