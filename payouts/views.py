from django.shortcuts import render

from accounts.decorators import role_required
from accounts.models import User

from .models import Payout
from .services import next_payout_time, rider_balance

rider_only = role_required(User.Role.RIDER)
vendor_only = role_required(User.Role.VENDOR)


@rider_only
def rider_earnings(request):
    payouts = Payout.objects.filter(
        kind=Payout.Kind.RIDER, recipient=request.user
    )[:15]
    return render(
        request,
        "payouts/rider_earnings.html",
        {
            "summary": rider_balance(request.user),
            "payouts": payouts,
            "next_payout": next_payout_time(),
        },
    )


@vendor_only
def vendor_payouts(request):
    payouts = (
        Payout.objects.filter(kind=Payout.Kind.VENDOR, recipient=request.user)
        .prefetch_related("lines__ledger_entry__order")[:50]
    )
    return render(request, "payouts/vendor_payouts.html", {"payouts": payouts})
