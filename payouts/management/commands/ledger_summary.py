from django.core.management.base import BaseCommand
from django.db.models import Count, Sum

from payments.models import LedgerEntry


class Command(BaseCommand):
    help = "Print totals of every kind of ledger entry, and how much is still unpaid."

    def handle(self, *args, **options):
        self.stdout.write("Ledger totals (KSh)")
        for value, label in LedgerEntry.Kind.choices:
            rows = LedgerEntry.objects.filter(kind=value)
            total = rows.aggregate(total=Sum("amount"), n=Count("id"))
            unpaid = rows.filter(payout_line__isnull=True).aggregate(total=Sum("amount"), n=Count("id"))
            self.stdout.write(
                f"  {label}: {total['total'] or 0} in {total['n']} entries; "
                f"{unpaid['total'] or 0} in {unpaid['n']} not yet paid out"
            )
        self.stdout.write(
            "Note: 'Payment received' counts all money taken, including orders still in progress."
        )
