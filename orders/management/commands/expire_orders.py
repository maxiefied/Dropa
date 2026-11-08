from django.core.management.base import BaseCommand

from orders.services import expire_overdue_orders


class Command(BaseCommand):
    help = "Expire orders whose shop-response or payment deadline has passed."

    def handle(self, *args, **options):
        count = expire_overdue_orders()
        self.stdout.write(f"{count} order(s) expired.")
