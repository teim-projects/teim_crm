
class UniversalProductIdentity:
    """Creates a CRM-independent identity for a product."""

    @staticmethod
    def build(source_crm, source_product_id):
        if source_crm is None or not str(source_crm).strip():
            raise ValueError("source_crm is required")

        if source_product_id is None or not str(source_product_id).strip():
            raise ValueError("source_product_id is required")

        crm = str(source_crm).strip().lower()
        product_id = str(source_product_id).strip()

        return {
            "source_crm": crm,
            "source_product_id": product_id,
            "product_key": f"{crm}:{product_id}",
        }
