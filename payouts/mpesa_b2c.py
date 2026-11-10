"""M-Pesa money-out gateway. This is the SIMULATED version for the prototype.

When you move to the real Daraja B2C API, send_money() is the only function
that changes: it sends the transfer and reports success or failure.

To test a failed transfer, add this to settings.py, then remove it again:
    DROPA_SIMULATED_PAYOUT_RESULT = "fail"
"""
import secrets
import string

from django.conf import settings

CHARS = string.ascii_uppercase + string.digits


def send_money(*, phone, amount, reference):
    """Return (success, mpesa_reference, failure_reason)."""
    if getattr(settings, "DROPA_SIMULATED_PAYOUT_RESULT", "success") == "fail":
        return False, "", "Simulated failure: the transfer was not accepted."
    return True, "SIM" + "".join(secrets.choice(CHARS) for _ in range(7)), ""
