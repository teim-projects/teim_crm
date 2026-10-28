from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW COLUMNS FROM crmapp_quotation_management")
    columns = cursor.fetchall()

print("Actual quotation table columns:")
for column in columns:
    print(column[0], "|", column[1])
