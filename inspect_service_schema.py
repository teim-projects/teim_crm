from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SHOW TABLES LIKE '%service%'")
    print("\nSERVICE-RELATED TABLES:")
    print([row[0] for row in cursor.fetchall()])

    cursor.execute("SHOW CREATE TABLE crmapp_serviceproduct")
    print("\nSERVICEPRODUCT TABLE DEFINITION:")
    print(cursor.fetchone()[1])
