import re

s = open("createdatabase17092025.sql", encoding="utf-8").read()

p = re.search(r"INSERT INTO `crmapp_product` VALUES (.*?);", s, re.S)
products = {
    int(i): name
    for i, name, category in re.findall(r"\((\d+),'([^']*)','([^']*)'\)", p.group(1))
}

sp = re.search(r"INSERT INTO `crmapp_serviceproduct` VALUES (.*?);", s, re.S)

ids = re.findall(
    r"\(\d+,[^,]+,[^,]+,[^,]+,[^,]+,(\d+),(\d+),",
    sp.group(1)
)

for product_id, service_id in ids:
    print(f"Service {service_id} | {products.get(int(product_id), 'UNKNOWN')}")
