exec(open("audit_cross_sell.py", encoding="utf-8-sig").read().split('print("\\n===== REAL SEVA CROSS-SELL COVERAGE =====")')[0])

print("\n===== MODEL DIAGNOSTICS =====")
print("Learned rules:", len(getattr(model, "rules", [])))
print("Customers with purchase history:")
for customer in customers:
    cid = str(customer.id)
    history = [r for r in services + invoices if str(r.get("customer_id")) == cid]
    if not history:
        continue
    owned = {
        str(r.get("product_key") or f"seva:{r.get('product_id')}")
        for r in history if r.get("product_id") is not None
    }
    predictions = model.recommend(owned, limit=10)
    valid = [
        p for p in predictions
        if p.get("product_key") in product_map
        and p.get("product_key") not in owned
    ]
    print(f"ID={customer.id} | history={len(history)} | owned={len(owned)} | raw={len(predictions)} | valid={len(valid)}")
