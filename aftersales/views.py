from django.contrib import messages
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from marketplace.views import get_vendor
from orders.models import Order
from payments.models import Payment

from .forms import ComplaintForm, RatingForm
from .models import Complaint, Rating
from .services import complaint_block_reason

customer_only = role_required(User.Role.CUSTOMER)
vendor_only = role_required(User.Role.VENDOR)
rider_only = role_required(User.Role.RIDER)


def own_order(request, pk):
    return get_object_or_404(
        Order.objects.select_related("vendor", "rider"), pk=pk, customer=request.user
    )


# ----- Ratings -----


@customer_only
def rate(request, pk):
    order = own_order(request, pk)

    if order.status != Order.Status.DELIVERED:
        messages.error(request, "You can rate an order once it has been delivered.")
        return redirect("orders:order_detail", pk=order.pk)
    if Rating.objects.filter(order=order).exists():
        messages.info(request, "You've already rated this order.")
        return redirect("orders:order_detail", pk=order.pk)

    if request.method == "POST":
        form = RatingForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                Rating.objects.create(
                    order=order,
                    vendor=order.vendor,
                    vendor_rating=data["vendor_rating"],
                    vendor_comment=data["vendor_comment"].strip(),
                    rider=order.rider,
                    rider_rating=data["rider_rating"],
                    rider_comment=data["rider_comment"].strip(),
                )
            except IntegrityError:
                messages.info(request, "You've already rated this order.")
            else:
                messages.success(request, "Thanks for your feedback.")
            return redirect("orders:order_detail", pk=order.pk)
    else:
        form = RatingForm()

    return render(request, "aftersales/rate.html", {"order": order, "form": form})


# ----- Receipt -----


@customer_only
def receipt(request, pk):
    order = own_order(request, pk)
    if order.paid_at is None:
        messages.error(request, "A receipt is available once the order has been paid.")
        return redirect("orders:order_detail", pk=order.pk)

    payment = order.payments.filter(status=Payment.Status.SUCCESS).first()
    return render(
        request,
        "aftersales/receipt.html",
        {"order": order, "items": order.items.all(), "payment": payment},
    )


# ----- Complaints -----


@customer_only
def complain(request, pk):
    order = own_order(request, pk)

    reason = complaint_block_reason(order)
    if reason:
        messages.error(request, reason)
        return redirect("orders:order_detail", pk=order.pk)

    if request.method == "POST":
        form = ComplaintForm(request.POST, request.FILES)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.order = order
            try:
                complaint.save()
            except IntegrityError:
                messages.error(request, "You've already reported a problem with this order.")
            else:
                messages.success(
                    request,
                    "Your complaint has been sent. The shop and rider can respond, "
                    "then Dropa will review it.",
                )
            return redirect("orders:order_detail", pk=order.pk)
    else:
        form = ComplaintForm()

    return render(
        request,
        "marketplace/form.html",
        {
            "form": form,
            "title": f"Report a problem with {order.order_number}",
            "submit_label": "Send complaint",
            "back_url": reverse("orders:order_detail", args=[order.pk]),
        },
    )


def save_response(request, complaint, role):
    text = request.POST.get("response", "").strip()
    if not text:
        messages.error(request, "Write your response before sending it.")
        return False
    if complaint.status != Complaint.Status.OPEN:
        messages.error(request, "This complaint has already been resolved.")
        return False

    setattr(complaint, f"{role}_response", text[:1000])
    setattr(complaint, f"{role}_responded_at", timezone.now())
    complaint.save(update_fields=[f"{role}_response", f"{role}_responded_at"])
    messages.success(request, "Your response has been sent to Dropa.")
    return True


@vendor_only
@require_POST
def vendor_respond(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    order = get_object_or_404(Order, pk=pk, vendor=vendor)
    complaint = get_object_or_404(Complaint, order=order)
    save_response(request, complaint, "vendor")
    return redirect("orders:vendor_order_detail", pk=order.pk)


@rider_only
@require_POST
def rider_respond(request, pk):
    order = get_object_or_404(Order, pk=pk, rider=request.user)
    complaint = get_object_or_404(Complaint, order=order)
    save_response(request, complaint, "rider")
    return redirect("riders:delivery_detail", pk=order.pk)
