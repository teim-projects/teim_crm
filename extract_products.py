import re

s = open("createdatabase17092025.sql", encoding="utf-8").read()

p = re.search(r"INSERT INTO `crmapp_product` VALUES (.*?);", s, re.S)
products = re.findall(r"\((\d+),'([^']*)','([^']*)'\)", p.group(1))
product_map = {int(i): (name, category) for i, name, category in products}

sp = re.search(r"INSERT INTO `crmapp_serviceproduct` VALUES (.*?);", s, re.S)

rows = re.findall(
    r"\((\d+),([\d.]+),([\d.]+),([\d.]+),(NULL|[\d.]+),(\d+),(\d+),'(.*?)'\)",
    sp.group(1)
)

for row in rows:
    _, price, qty, gst, total, product_id, service_id, desc = row
    name, category = product_map.get(int(product_id), ("UNKNOWN", "UNKNOWN"))
    print(f"Service {service_id} | Product {product_id} | {name} | {category} | Qty {qty}")

print(f"\nTOTAL RECORDS: {len(rows)}")
