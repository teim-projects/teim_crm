from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW COLUMNS FROM crmapp_service_management")
    print("SERVICE MANAGEMENT COLUMNS:")
    print([row[0] for row in cursor.fetchall()])

    cursor.execute("SHOW CREATE TABLE crmapp_service_management")
    print("\nSERVICE MANAGEMENT TABLE DEFINITION:")
    print(cursor.fetchone()[1])
