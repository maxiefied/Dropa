import math
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from orders.models import InvalidTransition, Order

from .models import LedgerEntry, Payment
from .mpesa import initiate_stk_push


class PaymentError(Exception):
    """A problem the customer should be told about in plain words."""


def cooldown_seconds():
    return getattr(settings, "DROPA_PAYMENT_COOLDOWN_SECONDS", 60)


def _remaining(last_payment):
    if last_payment is None:
        return 0
    end = last_payment.created_at + timedelta(seconds=cooldown_seconds())
    return max(0, math.ceil((end - timezone.now()).total_seconds()))


def order_cooldown_remaining(order):
    return _remaining(order.payments.order_by("-created_at").first())


def phone_cooldown_remaining(phone):
    return _remaining(Payment.objects.filter(phone=phone).order_by("-created_at").first())


def payment_block_reason(order):
    """Return why this order can't be paid right now, or None if it can."""
    if order.status == Order.Status.PAID:
        return "This order is already paid."
    if order.status == Order.Status.EXPIRED:
        return "The payment window ended, so this order expired."
    if order.status != Order.Status.ACCEPTED:
        return "This order can't be paid for any more."
    if order.payment_deadline and timezone.now() > order.payment_deadline:
        return "The payment window has ended."
    return None


@transaction.atomic
def start_payment(order, phone):
    """Send a new prompt, if the order is payable and the cooldown allows it."""
    reason = payment_block_reason(order)
    if reason:
        raise PaymentError(reason)

    wait = max(order_cooldown_remaining(order), phone_cooldown_remaining(phone))
    if wait:
        raise PaymentError(
            f"Please wait {wait} seconds before sending another prompt."
        )

    # Only one live prompt at a time: older unanswered ones are replaced.
    Payment.objects.filter(order=order, status=Payment.Status.PENDING).update(
        status=Payment.Status.FAILED,
        result_description="Replaced by a newer prompt",
    )
    checkout_id = initiate_stk_push(
        phone=phone, amount=order.total, order_number=order.order_number
    )
    return Payment.objects.create(
        order=order,
        phone=phone,
        amount=order.total,
        checkout_request_id=checkout_id,
    )


@transaction.atomic
def record_payment_result(payment, *, success, receipt_number="", description=""):
    """Apply M-Pesa's answer to a prompt. Safe to call twice for the same prompt."""
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != Payment.Status.PENDING:
        return payment  # already settled, ignore duplicates

    payment.result_description = description[:200]

    if not success:
        payment.status = Payment.Status.FAILED
        payment.save()
        return payment

    payment.receipt_number = receipt_number
    order = Order.objects.get(pk=payment.order_id)

    paid_in_time = False
    if order.status == Order.Status.ACCEPTED:
        try:
            order.move_to(
                Order.Status.PAID,
                by=order.customer,
                note=f"Paid via M-Pesa ({receipt_number})",
            )
            paid_in_time = True
        except InvalidTransition:
            paid_in_time = False

    payment.status = Payment.Status.SUCCESS if paid_in_time else Payment.Status.LATE
    payment.save()

    LedgerEntry.objects.create(
        order=order,
        payment=payment,
        kind=LedgerEntry.Kind.PAYMENT_RECEIVED,
        amount=payment.amount,
        note=f"M-Pesa receipt {receipt_number}",
    )
    if not paid_in_time:
        # Money arrived after the order expired or was cancelled.
        LedgerEntry.objects.create(
            order=order,
            payment=payment,
            kind=LedgerEntry.Kind.REFUND_DUE,
            amount=payment.amount,
            note="Payment arrived after the order could no longer be paid",
        )
    return payment
