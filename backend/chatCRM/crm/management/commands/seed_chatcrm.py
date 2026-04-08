from django.core.management.base import BaseCommand
from crm.models import UserProfile, Inventory, Order
from datetime import date, timedelta

class Command(BaseCommand):
    help = "Seed chatcrm database with mock users, inventory, and orders"

    def handle(self, *args, **options):
        rahim, _ = UserProfile.objects.get_or_create(
            email="rahim@example.com",
            defaults={"name": "Rahim", "phone": "01700000000"},
        )
        karim, _ = UserProfile.objects.get_or_create(
            email="karim@example.com",
            defaults={"name": "Karim", "phone": "01800000000"},
        )

        tshirt1, _ = Inventory.objects.get_or_create(
            product_code="t-shirt-01",
            defaults={
                "product_name": "Classic Cotton T-Shirt",
                "quantity": 50,
                "price": 650.00,
                "description": "Soft cotton tee, available in multiple sizes.",
            },
        )
        tshirt2, _ = Inventory.objects.get_or_create(
            product_code="t-shirt-02",
            defaults={
                "product_name": "Premium Black T-Shirt",
                "quantity": 20,
                "price": 990.00,
                "description": "Premium fit black t-shirt for casual wear.",
            },
        )
        jeans1, _ = Inventory.objects.get_or_create(
            product_code="jeans-01",
            defaults={
                "product_name": "Slim Fit Blue Jeans",
                "quantity": 15,
                "price": 1800.00,
                "description": "Stretch denim jeans with slim fit design.",
            },
        )

        Order.objects.get_or_create(
                    order_id="ORD12345",
                    defaults={
                        "user": rahim,
                        "product": tshirt1,
                        "quantity": 2,
                        "status": "shipped",
                        "delivery_date": date.today() + timedelta(days=2),
                    },
                )

        Order.objects.get_or_create(
            order_id="ORD12346",
            defaults={
                "user": rahim,
                "product": jeans1,
                "quantity": 1,
                "status": "delivered",
                "delivery_date": date.today() - timedelta(days=1),
            },
        )

        Order.objects.get_or_create(
            order_id="ORD55555",
            defaults={
                "user": karim,
                "product": tshirt2,
                "quantity": 1,
                "status": "processing",
                "delivery_date": date.today() + timedelta(days=5),
            },
        )

        self.stdout.write(self.style.SUCCESS("Seed data inserted successfully."))