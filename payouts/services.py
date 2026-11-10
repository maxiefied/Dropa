import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from payments.models import LedgerEntry, Payment

from .models import Payout, PayoutLine
from .mpesa_b2c import send_money

logger = logging.getLogger(__name__)

RIDER_KINDS = (LedgerEntry.Kind.RIDER_EARNING, LedgerEntry.Kind.RIDER_DEDUCTION)


def rider_payout_hour():
    return getattr(settings, "DROPA_RIDER_PAYOUT_HOUR", 18)


# ----- 6pm schedule -----


def last_cutoff(now=None):
    """The most recent payout time (6pm local by default)."""
    now = timezone.localtime(now or timezone.now())
    cutoff = now.replace(hour=rider_payout_hour(), minute=0, second=0, microsecond=0)
    if cutoff > now:
        cutoff -= timedelta(days=1)
    return cutoff


def next_payout_time(now=None):
    now = timezone.localtime(now or timezone.now())
    upcoming = now.replace(hour=rider_payout_hour(), minute=0, second=0, microsecond=0)
    if upcoming <= now:
        upcoming += timedelta(days=1)
    return upcoming


# ----- Creating and sending payouts -----


@transaction.atomic
def create_payout(*, kind, recipient, phone, amount, entries, period_end=None, note=""):
    payout = Payout.objects.create(
        kind=kind,
        recipient=recipient,
        phone=phone,
        amount=amount,
        period_end=period_end,
        note=note[:200],
    )
    PayoutLine.objects.bulk_create(
        [PayoutLine(payout=payout, ledger_entry=entry) for entry in entries]
    )
    return payout


def send_payout(payout):
    """Send (or retry) one payout. A payout that is already sent is never re-sent."""
    with transaction.atomic():
        payout = Payout.objects.select_for_update().get(pk=payout.pk)
        if payout.status == Payout.Status.SENT:
            return payout

        success, reference, reason = send_money(
            phone=payout.phone, amount=payout.amount, reference=f"DROPA-{payout.pk}"
        )
        if success:
            payout.status = Payout.Status.SENT
            payout.reference = reference
            payout.failure_reason = ""
            payout.sent_at = timezone.now()
        else:
            payout.status = Payout.Status.FAILED
            payout.failure_reason = reason[:200]
        payout.save()
    return payout


def retry_failed_payouts():
    results = []
    for payout in Payout.objects.filter(status=Payout.Status.FAILED):
        results.append(send_payout(payout))
    return results


# ----- Vendors: paid at pickup -----


def pay_vendor_entry(entry_pk):
    """Pay one vendor ledger entry right away. Never raises: a failure is logged
    and the entry stays unpaid so the next run can pick it up."""
    try:
        entry = LedgerEntry.objects.select_related("beneficiary").get(
            pk=entry_pk,
            kind=LedgerEntry.Kind.VENDOR_PAYOUT,
            payout_line__isnull=True,
        )
    except LedgerEntry.DoesNotExist:
        return None

    if entry.amount <= 0 or entry.beneficiary is None:
        return None

    try:
        payout = create_payout(
            kind=Payout.Kind.VENDOR,
            recipient=entry.beneficiary,
            phone=entry.beneficiary.phone,
            amount=entry.amount,
            entries=[entry],
            note=entry.note,
        )
        return send_payout(payout)
    except Exception:
        logger.exception("Vendor payout failed for ledger entry %s", entry_pk)
        return None


def run_vendor_payouts():
    """Catch up on any vendor entries that were not paid at pickup."""
    entry_ids = LedgerEntry.objects.filter(
        kind=LedgerEntry.Kind.VENDOR_PAYOUT, payout_line__isnull=True, amount__gt=0
    ).values_list("pk", flat=True)
    return [pay_vendor_entry(pk) for pk in entry_ids]


# ----- Customers: refunds -----


def refund_phone(entry):
    """Refunds go back to the number that paid."""
    if entry.payment_id:
        return entry.payment.phone
    payment = entry.order.payments.filter(status=Payment.Status.SUCCESS).first()
    return payment.phone if payment else entry.order.customer.phone


def run_refunds():
    entries = LedgerEntry.objects.filter(
        kind=LedgerEntry.Kind.REFUND_DUE, payout_line__isnull=True, amount__gt=0
    ).select_related("order__customer", "payment")
    results = []
    for entry in entries:
        payout = create_payout(
            kind=Payout.Kind.REFUND,
            recipient=entry.order.customer,
            phone=refund_phone(entry),
            amount=entry.amount,
            entries=[entry],
            note=f"Refund for {entry.order.order_number}",
        )
        results.append(send_payout(payout))
    return results


# ----- Riders: daily run -----


def rider_balance(user):
    """What a rider is owed right now, before the next run."""
    entries = list(
        LedgerEntry.objects.filter(
            beneficiary=user, kind__in=RIDER_KINDS, payout_line__isnull=True
        )
        .select_related("order")
        .order_by("-created_at")
    )
    earned = sum(
        (e.amount for e in entries if e.kind == LedgerEntry.Kind.RIDER_EARNING),
        Decimal("0"),
    )
    deducted = sum(
        (e.amount for e in entries if e.kind == LedgerEntry.Kind.RIDER_DEDUCTION),
        Decimal("0"),
    )
    return {
        "entries": entries,
        "earned": earned,
        "deducted": deducted,
        "balance": earned - deducted,
    }


def run_rider_payouts(cutoff):
    """Pay each rider what they earned up to `cutoff`, minus deductions.

    If a rider's total is zero or negative, nothing is sent and everything
    carries over to the next run.
    Returns a list of (rider, net_amount, payout_or_None).
    """
    entries = LedgerEntry.objects.filter(
        kind__in=RIDER_KINDS,
        payout_line__isnull=True,
        created_at__lte=cutoff,
        beneficiary__isnull=False,
    ).select_related("beneficiary")

    by_rider = defaultdict(list)
    for entry in entries:
        by_rider[entry.beneficiary_id].append(entry)

    results = []
    for rider_entries in by_rider.values():
        rider = rider_entries[0].beneficiary
        net = sum(
            (
                e.amount if e.kind == LedgerEntry.Kind.RIDER_EARNING else -e.amount
                for e in rider_entries
            ),
            Decimal("0"),
        )
        if net <= 0:
            results.append((rider, net, None))
            continue

        payout = create_payout(
            kind=Payout.Kind.RIDER,
            recipient=rider,
            phone=rider.phone,
            amount=net,
            entries=rider_entries,
            period_end=cutoff,
            note=f"{len(rider_entries)} item(s) up to {timezone.localtime(cutoff):%d %b %H:%M}",
        )
        results.append((rider, net, send_payout(payout)))
    return results
