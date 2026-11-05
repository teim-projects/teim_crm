
import os
import MySQLdb
import pandas as pd


DB_CONFIG = {
    "host": os.getenv("CRM_DB_HOST", "localhost"),
    "user": os.getenv("CRM_DB_USER", "crm_recommendation_reader"),
    "passwd": os.getenv("CRM_DB_PASSWORD"),
    "db": os.getenv("CRM_DB_NAME", "crmdb"),
    "port": int(os.getenv("CRM_DB_PORT", "3306")),
    "charset": "utf8mb4",
}

INTERACTION_COLUMNS = [
    "customer_id", "product_id", "category",
    "event_type", "event_date", "event_status",
    "quantity", "amount", "confidence_weight",
    "data_source", "source_table", "source_record_id",
    "event_date_iso",
]


def get_connection():
    if not DB_CONFIG["passwd"]:
        raise EnvironmentError(
            "CRM_DB_PASSWORD is not set in PowerShell."
        )

    return MySQLdb.connect(**DB_CONFIG)


def read_query(query):
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [item[0] for item in cursor.description]
        cursor.close()
        return pd.DataFrame(rows, columns=columns)
    finally:
        connection.close()


def load_customers():
    query = """
        SELECT
            id AS customer_id,
            fullname AS customer_name,
            customerid AS crm_customer_id,
            customer_type,
            shifttopartycity AS city,
            shifttopartystate AS state
        FROM crmapp_customer_details
        ORDER BY fullname
    """

    customers = read_query(query)

    customers["customer_id"] = (
        customers["customer_id"].astype(str)
    )

    customers["customer_name"] = (
        customers["customer_name"].fillna("").astype(str)
    )

    customers["crm_customer_id"] = (
        customers["crm_customer_id"].fillna("").astype(str)
    )

    return customers.drop_duplicates(
        subset=["customer_id"]
    )


def load_products():
    query = """
        SELECT product_id, product_name, category
        FROM crmapp_product
        ORDER BY product_id
    """

    products = read_query(query)
    products["product_id"] = pd.to_numeric(
        products["product_id"], errors="coerce"
    )
    products = products.dropna(subset=["product_id"]).copy()
    products["product_id"] = products["product_id"].astype(int)
    return products.drop_duplicates(subset=["product_id"])


def load_quotation_interactions():
    query = """
        SELECT
            q.customer_id,
            qs.product_id,
            p.category,
            'quotation_interest' AS event_type,
            q.quotation_date AS event_date,
            'latest_quotation' AS event_status,
            NULL AS quantity,
            NULL AS amount,
            1.5 AS confidence_weight,
            'real_crm' AS data_source,
            'crmapp_quotation_management_selected_services'
                AS source_table,
            qs.id AS source_record_id
        FROM crmapp_quotation_management q
        INNER JOIN crmapp_quotation_management_selected_services qs
            ON qs.quotation_management_id = q.id
        INNER JOIN crmapp_product p
            ON p.product_id = qs.product_id
        WHERE q.customer_id IS NOT NULL
          AND q.is_latest = 1
    """
    return read_query(query)


def load_service_interactions():
    query = """
        SELECT
            sm.customer_id,
            sp.product_id,
            p.category,
            CASE
                WHEN sm.is_approved = 1
                    THEN 'approved_service_product'
                ELSE 'nonapproved_service_product'
            END AS event_type,
            COALESCE(sm.service_date, sm.lead_date) AS event_date,
            CASE
                WHEN sm.is_approved = 1 THEN 'approved'
                ELSE 'not_approved'
            END AS event_status,
            sp.quantity,
            sp.price AS amount,
            CASE
                WHEN sm.is_approved = 1 THEN 3.0
                ELSE 0.75
            END AS confidence_weight,
            'real_crm' AS data_source,
            'crmapp_serviceproduct' AS source_table,
            sp.id AS source_record_id
        FROM crmapp_service_management sm
        INNER JOIN crmapp_serviceproduct sp
            ON sp.service_id = sm.id
        INNER JOIN crmapp_product p
            ON p.product_id = sp.product_id
        WHERE sm.customer_id IS NOT NULL
    """
    return read_query(query)


def load_completed_worklist_interactions():
    query = """
        SELECT DISTINCT
            sm.customer_id,
            sp.product_id,
            p.category,
            'completed_worklist_service_product' AS event_type,
            tw.completion_datetime AS event_date,
            'Completed' AS event_status,
            sp.quantity,
            sp.price AS amount,
            4.0 AS confidence_weight,
            'real_crm' AS data_source,
            'crmapp_techworklist' AS source_table,
            tw.id AS source_record_id
        FROM crmapp_techworklist tw
        INNER JOIN crmapp_service_management sm
            ON sm.id = tw.service_id
        INNER JOIN crmapp_serviceproduct sp
            ON sp.service_id = sm.id
        INNER JOIN crmapp_product p
            ON p.product_id = sp.product_id
        WHERE tw.status = 'Completed'
          AND sm.customer_id IS NOT NULL
    """
    return read_query(query)


def load_interactions():
    quotations = load_quotation_interactions()
    services = load_service_interactions()
    completed = load_completed_worklist_interactions()

    interactions = pd.concat(
        [quotations, services, completed],
        ignore_index=True
    )

    if interactions.empty:
        raise ValueError("No valid CRM interactions found.")

    interactions["customer_id"] = interactions["customer_id"].astype(str)
    interactions["product_id"] = pd.to_numeric(
        interactions["product_id"], errors="coerce"
    )
    interactions["confidence_weight"] = pd.to_numeric(
        interactions["confidence_weight"], errors="coerce"
    )
    interactions["event_date"] = pd.to_datetime(
        interactions["event_date"], errors="coerce"
    )

    interactions = interactions.dropna(
        subset=[
            "customer_id", "product_id", "category",
            "confidence_weight", "event_date"
        ]
    ).copy()

    interactions["product_id"] = interactions["product_id"].astype(int)
    interactions["source_record_id"] = (
        interactions["source_record_id"].astype(str)
    )

    interactions["event_date_iso"] = (
        interactions["event_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    )
    interactions["event_date"] = (
        interactions["event_date"].dt.strftime("%Y-%m-%d")
    )

    interactions = interactions[
        interactions["data_source"] == "real_crm"
    ].copy()

    return interactions[INTERACTION_COLUMNS]


def load_live_crm_data():
    print("\nConnecting to live CRM database...")

    customers = load_customers()
    print("Live customers:", len(customers))

    products = load_products()
    print("Live products:", len(products))

    interactions = load_interactions()
    print("Real CRM interactions:", len(interactions))

    print("\nInteraction breakdown:")
    print(interactions["event_type"].value_counts())

    return customers, products, interactions


if __name__ == "__main__":
    customers, products, interactions = load_live_crm_data()

    print("\nLIVE CRM DATA VALIDATION")
    print("Customers:", len(customers))
    print("Products:", len(products))
    print("Interactions:", len(interactions))
    print(
        "Synthetic interactions:",
        (interactions["data_source"] == "synthetic").sum()
    )
    print("Unique interaction customers:", interactions["customer_id"].nunique())
    print("Unique interaction products:", interactions["product_id"].nunique())

    print("\nFirst five interactions:")
    print(interactions.head().to_string(index=False))
