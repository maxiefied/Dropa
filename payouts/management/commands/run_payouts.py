from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from payouts import services


class Command(BaseCommand):
    help = (
        "Send refunds, retry vendor payouts, and pay riders for everything "
        "earned up to the last payout time (6pm by default)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--cutoff",
            help='Pay riders for everything up to this time: "now" or "YYYY-MM-DD HH:MM". '
            "Default: the most recent 6pm.",
        )

    def handle(self, *args, **options):
        raw = options["cutoff"]
        if raw is None:
            cutoff = services.last_cutoff()
        elif raw == "now":
            cutoff = timezone.now()
        else:
            try:
                cutoff = timezone.make_aware(datetime.strptime(raw, "%Y-%m-%d %H:%M"))
            except ValueError:
                raise CommandError('Use --cutoff "now" or --cutoff "YYYY-MM-DD HH:MM".')

        self.stdout.write(f"Rider cutoff: {timezone.localtime(cutoff):%Y-%m-%d %H:%M}")

        retried = services.retry_failed_payouts()
        self.stdout.write(f"Retried failed payouts: {len(retried)}")

        vendor_results = [p for p in services.run_vendor_payouts() if p]
        self.stdout.write(f"Vendor payouts sent now: {len(vendor_results)}")

        refunds = services.run_refunds()
        self.stdout.write(f"Refunds processed: {len(refunds)}")

        riders = services.run_rider_payouts(cutoff)
        paid = [r for r in riders if r[2] is not None]
        carried = [r for r in riders if r[2] is None]
        self.stdout.write(f"Riders paid: {len(paid)}")
        for rider, net, payout in paid:
            self.stdout.write(f"  {rider.name}: KSh {net} -> {payout.get_status_display()}")
        for rider, net, _ in carried:
            self.stdout.write(f"  {rider.name}: balance KSh {net}, carried over to the next run")
