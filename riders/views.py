from functools import wraps

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from orders.models import Order

from .forms import RiderDocumentForm, RiderPhotoForm
from .models import Rider
from .qr import qr_svg
from .services import (
    RiderError,
    active_orders_for,
    available_orders,
    claim_order,
    complete_delivery,
    mark_picked,
    max_active_orders,
)

rider_only = role_required(User.Role.RIDER)


def get_rider(user):
    return Rider.objects.filter(user=user).select_related("user").first()


def verified_rider_only(view):
    """Rider role, with a profile that has been verified. Sets request.rider."""

    @wraps(view)
    @rider_only
    def wrapper(request, *args, **kwargs):
        rider = get_rider(request.user)
        if rider is None or not rider.is_verified:
            messages.error(request, "You can do this once your rider profile is verified.")
            return redirect("riders:rider_home")
        request.rider = rider
        return view(request, *args, **kwargs)

    return wrapper


# ----- Profile and verification -----


@rider_only
def rider_home(request):
    rider = get_rider(request.user)
    if rider is None:
        return redirect("riders:profile_edit")
    return render(
        request,
        "riders/rider_home.html",
        {
            "rider": rider,
            "documents": rider.documents.all(),
            "doc_form": RiderDocumentForm(),
            "active_count": active_orders_for(request.user).count(),
        },
    )


@rider_only
def profile_edit(request):
    rider = get_rider(request.user)

    if request.method == "POST":
        form = RiderPhotoForm(request.POST, request.FILES, instance=rider)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Photo saved.")
            return redirect("riders:rider_home")
    else:
        form = RiderPhotoForm(instance=rider)

    back_url = reverse("riders:rider_home") if rider else reverse("accounts:dashboard")
    return render(
        request,
        "marketplace/form.html",
        {
            "form": form,
            "title": "Set up your rider profile" if rider is None else "Change your photo",
            "submit_label": "Save",
            "back_url": back_url,
        },
    )


@rider_only
@require_POST
def document_upload(request):
    rider = get_rider(request.user)
    if rider is None:
        return redirect("riders:profile_edit")

    form = RiderDocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.rider = rider
        document.save()
        messages.success(request, "Document uploaded. We'll review it soon.")
    else:
        messages.error(request, "Choose a document type and a file, then try again.")
    return redirect("riders:rider_home")


# ----- Name tag and public verification page -----


@verified_rider_only
def name_tag(request):
    rider = request.rider
    verify_url = request.build_absolute_uri(
        reverse("riders:verify", args=[rider.tag_token])
    )
    return render(
        request,
        "riders/name_tag.html",
        {"rider": rider, "qr_svg": qr_svg(verify_url), "verify_url": verify_url},
    )


def verify(request, token):
    """Public page the name tag's QR code opens. No login needed."""
    rider = Rider.objects.filter(tag_token=token).select_related("user").first()
    return render(
        request,
        "riders/verify.html",
        {"rider": rider},
        status=200 if rider else 404,
    )


# ----- Claiming and delivering -----


@verified_rider_only
def available(request):
    return render(
        request,
        "riders/available.html",
        {
            "orders": available_orders(),
            "active_count": active_orders_for(request.user).count(),
            "max_active": max_active_orders(),
        },
    )


@verified_rider_only
@require_POST
def claim(request, pk):
    try:
        order = claim_order(pk, request.user)
    except RiderError as error:
        messages.error(request, str(error))
        return redirect("riders:available")
    messages.success(request, f"You claimed {order.order_number}. Head to the shop.")
    return redirect("riders:delivery_detail", pk=order.pk)


@verified_rider_only
def deliveries(request):
    mine = Order.objects.filter(rider=request.user).select_related("vendor")
    active = [order for order in mine if order.status in ("paid", "picked")]
    recent = [order for order in mine if order.status == "delivered"][:15]
    return render(
        request, "riders/deliveries.html", {"active": active, "recent": recent}
    )


@verified_rider_only
def delivery_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related("vendor__block", "customer"),
        pk=pk,
        rider=request.user,
    )
    return render(
        request,
        "riders/delivery_detail.html",
        {"order": order, "items": order.items.all()},
    )


@verified_rider_only
@require_POST
def picked(request, pk):
    try:
        mark_picked(pk, request.user)
        messages.success(request, "Marked as picked up. Take it to the customer.")
    except RiderError as error:
        messages.error(request, str(error))
    return redirect("riders:delivery_detail", pk=pk)


@verified_rider_only
@require_POST
def deliver(request, pk):
    try:
        order = complete_delivery(pk, request.user, request.POST.get("code", ""))
        messages.success(
            request, f"Delivered. KSh {order.rider_earnings:.0f} added to your earnings."
        )
        return redirect("riders:deliveries")
    except RiderError as error:
        messages.error(request, str(error))
    return redirect("riders:delivery_detail", pk=pk)
