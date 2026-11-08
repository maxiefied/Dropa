from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import (
    InvalidTransition,
    Order,
    OrderItem,
    OrderStatusHistory,
    vendor_response_minutes,
)


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_totals(vendor, lines):
    """lines is a list of (menu_item, quantity). Prices come from the database."""
    zone = vendor.zone
    goods_total = sum((item.price * qty for item, qty in lines), Decimal("0"))
    delivery_fee = zone.flat_delivery_fee
    service_fee = zone.service_fee
    commission = goods_total * zone.vendor_commission_percent / Decimal("100")
    rider_earnings = delivery_fee * Decimal(zone.rider_share_percent) / Decimal("100")
    return {
        "goods_total": money(goods_total),
        "delivery_fee": money(delivery_fee),
        "service_fee": money(service_fee),
        "total": money(goods_total + delivery_fee + service_fee),
        "rider_earnings": money(rider_earnings),
        "vendor_payout": money(goods_total - commission),
    }


@transaction.atomic
def place_order(*, customer, vendor, lines, address):
    """Create the order, its items and the first history row."""
    totals = calculate_totals(vendor, lines)
    block = address["block"]
    now = timezone.now()

    order = Order.objects.create(
        customer=customer,
        vendor=vendor,
        address_block=block.name if block else address["other_location"].strip(),
        address_is_other=block is None,
        address_floor=address["floor"].strip(),
        address_room=address["room"].strip(),
        rider_note=(address.get("rider_note") or "").strip(),
        vendor_response_deadline=now + timedelta(minutes=vendor_response_minutes()),
        **totals,
    )
    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                menu_item=item,
                name=item.name,
                unit_price=item.price,
                quantity=qty,
            )
            for item, qty in lines
        ]
    )
    OrderStatusHistory.objects.create(
        order=order, status=Order.Status.PLACED, changed_by=customer
    )
    return order


def expire_overdue_orders():
    """Expire orders the shop didn't answer, or the customer didn't pay for."""
    now = timezone.now()
    overdue = Order.objects.filter(
        Q(status=Order.Status.PLACED, vendor_response_deadline__lt=now)
        | Q(status=Order.Status.ACCEPTED, payment_deadline__lt=now)
    )
    count = 0
    for order in overdue:
        note = (
            "The shop did not respond in time"
            if order.status == Order.Status.PLACED
            else "The payment window ended"
        )
        try:
            order.move_to(Order.Status.EXPIRED, note=note)
            count += 1
        except InvalidTransition:
            continue
    return count
