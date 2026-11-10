"""Builds the bottom navigation bar for each role, with small count badges."""
import logging

from django.urls import reverse

logger = logging.getLogger(__name__)

# (key, label, url name, icon, view-name prefixes that make the tab "active")
NAV = {
    "customer": [
        ("shops", "Shops", "marketplace:shop_list", "bi-shop",
         ["marketplace:shop_list", "marketplace:shop_detail", "orders:checkout"]),
        ("orders", "Orders", "orders:order_list", "bi-receipt",
         ["orders:order_list", "orders:order_detail", "orders:order_cancel", "payments:", "aftersales:"]),
    ],
    "vendor": [
        ("orders", "Orders", "orders:vendor_orders", "bi-bag",
         ["orders:vendor_order", "orders:order_accept", "orders:order_reject", "orders:order_ready", "aftersales:vendor_respond"]),
        ("shop", "Shop", "marketplace:vendor_home", "bi-shop",
         ["marketplace:vendor_home", "marketplace:shop_edit", "marketplace:menu_item", "marketplace:document_upload", "marketplace:toggle_open"]),
        ("payouts", "Payouts", "payouts:vendor_payouts", "bi-cash-coin",
         ["payouts:vendor_payouts"]),
    ],
    "rider": [
        ("available", "Available", "riders:available", "bi-box-seam",
         ["riders:available", "riders:claim"]),
        ("deliveries", "Deliveries", "riders:deliveries", "bi-bicycle",
         ["riders:deliveries", "riders:delivery_detail", "riders:picked", "riders:deliver", "aftersales:rider_respond"]),
        ("earnings", "Earnings", "payouts:rider_earnings", "bi-wallet2",
         ["payouts:rider_earnings"]),
        ("me", "Me", "riders:rider_home", "bi-person",
         ["riders:rider_home", "riders:profile_edit", "riders:name_tag", "riders:document_upload"]),
    ],
}


def is_active(view_name, prefixes):
    return any(view_name.startswith(prefix) for prefix in prefixes)


def badge_counts(user):
    """Small numbers that tell people something needs them."""
    from orders.models import Order

    if user.role == "customer":
        # Orders accepted by the shop and waiting for this customer to pay.
        return {"orders": Order.objects.filter(customer=user, status=Order.Status.ACCEPTED).count()}
    if user.role == "vendor":
        # New orders waiting for the shop to accept or reject.
        return {"orders": Order.objects.filter(vendor__owner=user, status=Order.Status.PLACED).count()}
    if user.role == "rider":
        from riders.models import Rider

        if Rider.objects.filter(user=user, status=Rider.Status.APPROVED).exists():
            return {
                "available": Order.objects.filter(
                    status=Order.Status.PAID, rider__isnull=True
                ).count()
            }
    return {}


def navigation(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    definition = NAV.get(user.role)
    if not definition:
        return {}

    match = getattr(request, "resolver_match", None)
    view_name = match.view_name if match else ""

    try:
        badges = badge_counts(user)
    except Exception:  # a badge problem must never break a page
        logger.exception("Could not work out navigation badges")
        badges = {}

    return {
        "nav_items": [
            {
                "label": label,
                "url": reverse(url_name),
                "icon": icon,
                "active": is_active(view_name, prefixes),
                "badge": badges.get(key, 0),
            }
            for key, label, url_name, icon, prefixes in definition
        ]
    }
