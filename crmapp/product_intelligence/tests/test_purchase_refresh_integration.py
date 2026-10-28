from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, Client
from django.urls import reverse

from crmapp.models import (
    customer_details,
    Product,
    service_management,
    ServiceProduct,
)
from crmapp.product_intelligence.adapters.seva.service import (
    SevaServiceAdapter,
)


class PurchaseRefreshIntegrationTest(TestCase):
    def test_new_database_purchase_is_visible_to_adapter_and_next_endpoint_request(self):
        customer = customer_details.objects.create(
            fullname="Refresh Integration Test Customer",
            primarycontact=9000000001,
            designation="Test Contact",
            shifttopartyaddress="Test Address",
            shifttopartycity="Pune",
            shifttopartystate="Maharashtra",
            shifttopartypostal="411001",
            soldtopartyaddress="Test Address",
            soldtopartycity="Pune",
            soldtopartystate="Maharashtra",
            soldtopartypostal="411001",
        )
        product = Product.objects.create(
            product_name="Refresh Integration Test Product",
            category="Product Sale",
        )
        service = service_management.objects.create(
            customer=customer,
            is_approved=True,
            service_subject="Refresh integration test",
            state="Maharashtra",
            city="Pune",
            address="Test address",
            contract_type="NOT SELECTED",
            contract_status="NOT SELECTED",
            frequency_count="NOT SELECTED",
            payment_terms="Test",
        )

        purchase = ServiceProduct.objects.create(
            service=service,
            product=product,
            price=Decimal("100.00"),
            quantity=Decimal("1.00"),
            gst_percentage=Decimal("18.00"),
            total_with_gst=Decimal("118.00"),
        )

        adapter = SevaServiceAdapter()
        records = adapter.get_universal_service_products()

        self.assertTrue(
            any(
                str(record.get("product_id")) == str(product.pk)
                or str(record.get("source_product_id")) == str(product.pk)
                for record in records
            ),
            "Newly saved purchase was not found by the SEVA service adapter.",
        )

        client = Client()
        response = client.post(
            reverse("product_recommendations"),
            {
                "customer_id": str(customer.pk),
                "mode": "CROSS_SELL",
            },
            HTTP_HOST="localhost",
        )

        self.assertIn(response.status_code, (200, 302))
        self.assertNotIn(
            b"Could not generate recommendations",
            response.content,
        )
        self.assertTrue(
            ServiceProduct.objects.filter(pk=purchase.pk).exists()
        )

