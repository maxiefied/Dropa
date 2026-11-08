from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from orders.models import Order

from .models import Complaint


def complaint_window_hours():
    return getattr(settings, "DROPA_COMPLAINT_WINDOW_HOURS", 24)


def complaint_block_reason(order):
    """Return why a complaint can't be opened for this order, or None if it can."""
    if Complaint.objects.filter(order=order).exists():
        return "You've already reported a problem with this order."

    if order.status in (Order.Status.PAID, Order.Status.PICKED):
        return None

    if order.status == Order.Status.DELIVERED:
        window = timedelta(hours=complaint_window_hours())
        if order.delivered_at and timezone.now() - order.delivered_at <= window:
            return None
        return "The time to report a problem with this order has passed."

    return "You can report a problem once your order has been paid."
