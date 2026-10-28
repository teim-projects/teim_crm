
import unittest

from crmapp.product_intelligence.universal_features.product_identity import (
    UniversalProductIdentity,
)


class TestUniversalProductIdentity(unittest.TestCase):
    def test_identity_includes_crm_and_product_id(self):
        identity = UniversalProductIdentity.build("SEVA", 1)

        self.assertEqual(identity["source_crm"], "seva")
        self.assertEqual(identity["source_product_id"], "1")
        self.assertEqual(identity["product_key"], "seva:1")

    def test_same_product_id_from_different_crms_stays_distinct(self):
        seva = UniversalProductIdentity.build("SEVA", 1)
        krishna = UniversalProductIdentity.build("Krishna", 1)

        self.assertNotEqual(
            seva["product_key"],
            krishna["product_key"],
        )

    def test_missing_identity_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            UniversalProductIdentity.build("", 1)

        with self.assertRaises(ValueError):
            UniversalProductIdentity.build("SEVA", None)


if __name__ == "__main__":
    unittest.main()
