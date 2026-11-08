from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from marketplace.models import Vendor
from marketplace.views import get_vendor

from .forms import CheckoutForm
from .models import InvalidTransition, Order, SavedAddress
from .services import calculate_totals, expire_overdue_orders, place_order

MAX_QUANTITY = 20

customer_only = role_required(User.Role.CUSTOMER)
vendor_only = role_required(User.Role.VENDOR)


# ----- Customer: basket and checkout -----


def load_cart(request):
    """Return (vendor, [(item, qty), ...]) from the session, or None."""
    cart = request.session.get("cart")
    if not cart:
        return None

    vendor = (
        Vendor.objects.filter(
            pk=cart.get("vendor_id"), status=Vendor.Status.APPROVED, is_open=True
        )
        .select_related("block__zone")
        .first()
    )
    if vendor is None:
        return None

    wanted = {int(pk): qty for pk, qty in cart.get("items", {}).items()}
    items = vendor.menu_items.filter(is_available=True, pk__in=wanted.keys())
    lines = [(item, wanted[item.pk]) for item in items]
    if not lines:
        return None
    return vendor, lines


@customer_only
@require_POST
def checkout_start(request):
    vendor_id = request.POST.get("vendor_id", "")
    vendor = None
    if vendor_id.isdigit():
        vendor = Vendor.objects.filter(
            pk=int(vendor_id), status=Vendor.Status.APPROVED, is_open=True
        ).first()
    if vendor is None:
        messages.error(request, "That shop isn't taking orders right now.")
        return redirect("marketplace:shop_list")

    cart_items = {}
    for item in vendor.menu_items.filter(is_available=True):
        try:
            qty = int(request.POST.get(f"qty_{item.pk}", "0"))
        except ValueError:
            qty = 0
        qty = max(0, min(qty, MAX_QUANTITY))
        if qty:
            cart_items[str(item.pk)] = qty

    if not cart_items:
        messages.error(request, "Choose at least one item.")
        return redirect("marketplace:shop_detail", pk=vendor.pk)

    request.session["cart"] = {"vendor_id": vendor.pk, "items": cart_items}
    return redirect("orders:checkout")


def initial_from_saved(saved):
    if saved is None:
        return {"save_address": True}
    return {
        "block": saved.block_id,
        "other_location": saved.other_text,
        "other_confirm": bool(saved.other_text),
        "floor": saved.floor,
        "room": saved.room,
        "save_address": False,
    }


@customer_only
def checkout(request):
    loaded = load_cart(request)
    if loaded is None:
        messages.error(
            request, "Your basket is empty or the shop is closed. Please start again."
        )
        return redirect("marketplace:shop_list")

    vendor, lines = loaded
    zone = vendor.zone
    saved = SavedAddress.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = CheckoutForm(request.POST, zone=zone)
        if form.is_valid():
            data = form.cleaned_data
            order = place_order(
                customer=request.user, vendor=vendor, lines=lines, address=data
            )
            if data["save_address"]:
                block = data["block"]
                SavedAddress.objects.update_or_create(
                    user=request.user,
                    defaults={
                        "block": block,
                        "other_text": "" if block else data["other_location"].strip(),
                        "floor": data["floor"].strip(),
                        "room": data["room"].strip(),
                    },
                )
            request.session.pop("cart", None)
            messages.success(
                request,
                f"Order {order.order_number} sent to {vendor.name}. "
                "You'll pay once they accept it.",
            )
            return redirect("orders:order_detail", pk=order.pk)
    else:
        form = CheckoutForm(zone=zone, initial=initial_from_saved(saved))

    rows = [{"item": item, "qty": qty, "total": item.price * qty} for item, qty in lines]
    return render(
        request,
        "orders/checkout.html",
        {
            "vendor": vendor,
            "rows": rows,
            "totals": calculate_totals(vendor, lines),
            "form": form,
            "saved": saved,
        },
    )


# ----- Customer: their orders -----


@customer_only
def order_list(request):
    expire_overdue_orders()
    orders = Order.objects.filter(customer=request.user).select_related("vendor")
    return render(request, "orders/order_list.html", {"orders": orders})


@customer_only
def order_detail(request, pk):
    expire_overdue_orders()
    order = get_object_or_404(
        Order.objects.select_related("vendor"), pk=pk, customer=request.user
    )
    return render(
        request,
        "orders/order_detail.html",
        {"order": order, "items": order.items.all(), "history": order.history.all()},
    )


@customer_only
@require_POST
def order_cancel(request, pk):
    expire_overdue_orders()
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    try:
        order.move_to(Order.Status.CANCELLED, by=request.user, note="Cancelled by customer")
        messages.success(request, f"Order {order.order_number} cancelled. Nothing was charged.")
    except InvalidTransition:
        messages.error(request, "This order can't be cancelled any more.")
    return redirect("orders:order_detail", pk=order.pk)


# ----- Vendor: incoming orders -----
# Vendors only ever see order numbers, items and their own payout.
# Nothing about the customer or the delivery address is sent to these pages.


@vendor_only
def vendor_orders(request):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    expire_overdue_orders()
    orders = Order.objects.filter(vendor=vendor).prefetch_related("items")
    active = [order for order in orders if order.is_active]
    past = [order for order in orders if not order.is_active][:20]
    return render(
        request,
        "orders/vendor_orders.html",
        {"vendor": vendor, "active": active, "past": past},
    )


@vendor_only
def vendor_order_detail(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    expire_overdue_orders()
    order = get_object_or_404(Order, pk=pk, vendor=vendor)
    return render(
        request,
        "orders/vendor_order_detail.html",
        {"vendor": vendor, "order": order, "items": order.items.all()},
    )


@vendor_only
@require_POST
def order_accept(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    expire_overdue_orders()
    order = get_object_or_404(Order, pk=pk, vendor=vendor)

    if not vendor.is_verified:
        messages.error(request, "Your shop must be verified to accept orders.")
    else:
        try:
            order.move_to(Order.Status.ACCEPTED, by=request.user, note="Accepted by shop")
            messages.success(
                request,
                "Order accepted. Wait for the customer to pay before you start preparing it.",
            )
        except InvalidTransition:
            messages.error(request, "This order can't be accepted any more.")
    return redirect("orders:vendor_order_detail", pk=order.pk)


@vendor_only
@require_POST
def order_reject(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    expire_overdue_orders()
    order = get_object_or_404(Order, pk=pk, vendor=vendor)
    try:
        order.move_to(Order.Status.REJECTED, by=request.user, note="Rejected by shop")
        messages.success(request, "Order rejected. The customer has not been charged.")
    except InvalidTransition:
        messages.error(request, "This order can't be rejected any more.")
    return redirect("orders:vendor_order_detail", pk=order.pk)


@vendor_only
@require_POST
def order_ready(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    expire_overdue_orders()
    order = get_object_or_404(Order, pk=pk, vendor=vendor)

    if order.status == Order.Status.ACCEPTED:
        messages.error(
            request, "The customer hasn't paid yet, so this order can't be marked ready."
        )
    else:
        try:
            order.mark_ready(by=request.user)
            messages.success(request, "Marked ready.")
        except InvalidTransition:
            messages.error(request, "This order can't be marked ready right now.")
    return redirect("orders:vendor_order_detail", pk=order.pk)
