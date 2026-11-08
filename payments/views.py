from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User
from orders.models import Order
from orders.services import expire_overdue_orders

from .forms import PayForm
from .models import Payment
from .mpesa import simulated_receipt
from .services import (
    PaymentError,
    order_cooldown_remaining,
    payment_block_reason,
    record_payment_result,
    start_payment,
)

customer_only = role_required(User.Role.CUSTOMER)


def simulation_enabled():
    return getattr(settings, "DROPA_SIMULATE_PAYMENTS", True)


@customer_only
def pay(request, pk):
    expire_overdue_orders()
    order = get_object_or_404(
        Order.objects.select_related("vendor"), pk=pk, customer=request.user
    )

    reason = payment_block_reason(order)
    if reason:
        messages.error(request, reason)
        return redirect("orders:order_detail", pk=order.pk)

    if request.method == "POST":
        form = PayForm(request.POST)
        if form.is_valid():
            try:
                payment = start_payment(order, form.cleaned_data["phone"])
            except PaymentError as error:
                messages.error(request, str(error))
            else:
                messages.success(
                    request,
                    f"M-Pesa prompt sent to {payment.phone_display}. "
                    "Enter your PIN on that phone.",
                )
            return redirect("payments:pay", pk=order.pk)
    else:
        form = PayForm(initial={"phone": "0" + request.user.phone[3:]})

    attempts = list(order.payments.all()[:5])
    pending = next((p for p in attempts if p.status == Payment.Status.PENDING), None)
    return render(
        request,
        "payments/pay.html",
        {
            "order": order,
            "form": form,
            "attempts": attempts,
            "pending": pending,
            "wait_seconds": order_cooldown_remaining(order),
            "simulation": simulation_enabled(),
        },
    )


@customer_only
@require_POST
def simulate(request, payment_id):
    """PROTOTYPE ONLY: stands in for what the customer does on their phone."""
    if not simulation_enabled():
        raise Http404

    expire_overdue_orders()
    payment = get_object_or_404(
        Payment, pk=payment_id, order__customer=request.user
    )
    result = request.POST.get("result")

    if payment.status != Payment.Status.PENDING:
        messages.info(request, "That prompt has already been answered.")
    elif result == "pay":
        payment = record_payment_result(
            payment,
            success=True,
            receipt_number=simulated_receipt(),
            description="The service request is processed successfully.",
        )
        if payment.status == Payment.Status.SUCCESS:
            messages.success(
                request, f"Payment received. M-Pesa receipt {payment.receipt_number}."
            )
            return redirect("orders:order_detail", pk=payment.order_id)
        messages.error(
            request,
            "Your payment arrived after the payment window ended. "
            "The order expired, and the money is marked for refund.",
        )
        return redirect("orders:order_detail", pk=payment.order_id)
    elif result == "cancel":
        record_payment_result(
            payment, success=False, description="Request cancelled by user"
        )
        messages.error(request, "The prompt was cancelled on the phone.")
    elif result == "wrong_pin":
        record_payment_result(
            payment, success=False, description="Wrong PIN entered"
        )
        messages.error(request, "Wrong PIN. Send a new prompt to try again.")
    else:
        messages.error(request, "Unknown action.")

    return redirect("payments:pay", pk=payment.order_id)
