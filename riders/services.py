import secrets

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from orders.models import InvalidTransition, Order, OrderStatusHistory
from payments.models import LedgerEntry


class RiderError(Exception):
    """A problem the rider should be told about in plain words."""


def max_active_orders():
    return getattr(settings, "DROPA_MAX_RIDER_ACTIVE_ORDERS", 3)


def max_code_attempts():
    return getattr(settings, "DROPA_MAX_CODE_ATTEMPTS", 5)


ACTIVE_STATUSES = (Order.Status.PAID, Order.Status.PICKED)


def active_orders_for(user):
    return Order.objects.filter(rider=user, status__in=ACTIVE_STATUSES)


def available_orders():
    """Paid orders that no rider has claimed yet, oldest first."""
    return (
        Order.objects.filter(status=Order.Status.PAID, rider__isnull=True)
        .select_related("vendor__block")
        .prefetch_related("items")
        .order_by("paid_at")
    )


@transaction.atomic
def claim_order(order_pk, user):
    if active_orders_for(user).count() >= max_active_orders():
        raise RiderError(
            f"You can hold up to {max_active_orders()} orders at once. "
            "Finish one before claiming another."
        )

    # The filter makes sure only one rider can win the claim.
    updated = Order.objects.filter(
        pk=order_pk, status=Order.Status.PAID, rider__isnull=True
    ).update(rider=user, claimed_at=timezone.now())
    if not updated:
        raise RiderError("Another rider claimed this order, or it's no longer available.")

    order = Order.objects.get(pk=order_pk)
    OrderStatusHistory.objects.create(
        order=order, status=order.status, changed_by=user, note="Claimed by rider"
    )
    return order


@transaction.atomic
def mark_picked(order_pk, user):
    order = (
        Order.objects.select_related("vendor__owner")
        .filter(pk=order_pk, rider=user)
        .first()
    )
    if order is None:
        raise RiderError("This isn't your order.")
    if order.status != Order.Status.PAID:
        raise RiderError("This order can't be marked as picked up.")
    if order.ready_at is None:
        raise RiderError("The shop hasn't marked this order ready yet.")

    try:
        order.move_to(Order.Status.PICKED, by=user, note="Picked up by rider")
    except InvalidTransition as error:
        raise RiderError(str(error))

    # The shop is paid at pickup.
    LedgerEntry.objects.create(
        order=order,
        kind=LedgerEntry.Kind.VENDOR_PAYOUT,
        beneficiary=order.vendor.owner,
        amount=order.vendor_payout,
        note=f"Released at pickup of {order.order_number}",
    )
    return order


def complete_delivery(order_pk, user, code):
    """Confirm delivery with the customer's code. Wrong guesses are counted
    and saved, so this function is deliberately not one big transaction."""
    order = Order.objects.filter(pk=order_pk, rider=user).first()
    if order is None:
        raise RiderError("This isn't your order.")
    if order.status != Order.Status.PICKED:
        raise RiderError("Mark the order as picked up before completing the delivery.")
    if not order.delivery_code:
        raise RiderError("This order has no delivery code. Contact Dropa support.")

    limit = max_code_attempts()
    if order.delivery_code_attempts >= limit:
        raise RiderError("Too many wrong codes. This delivery is locked, contact Dropa support.")

    code = (code or "").strip()
    if not (code.isascii() and code.isdigit() and len(code) == 4):
        raise RiderError("Enter the 4-digit code the customer gives you.")

    if not secrets.compare_digest(code, order.delivery_code):
        Order.objects.filter(pk=order.pk).update(
            delivery_code_attempts=F("delivery_code_attempts") + 1
        )
        left = limit - order.delivery_code_attempts - 1
        if left > 0:
            raise RiderError(f"Wrong code. {left} tries left.")
        raise RiderError("Wrong code. This delivery is now locked, contact Dropa support.")

    with transaction.atomic():
        try:
            order.move_to(
                Order.Status.DELIVERED, by=user, note="Delivered, code confirmed"
            )
        except InvalidTransition as error:
            raise RiderError(str(error))
        LedgerEntry.objects.create(
            order=order,
            kind=LedgerEntry.Kind.RIDER_EARNING,
            beneficiary=user,
            amount=order.rider_earnings,
            note=f"Delivery of {order.order_number}",
        )
    return order
