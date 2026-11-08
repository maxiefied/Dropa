"""M-Pesa gateway. This is the SIMULATED version used by the prototype.

When you move to the real Daraja API, only two things change:
  1. initiate_stk_push() sends a real STK push and returns Safaricom's
     CheckoutRequestID.
  2. A new callback view receives Safaricom's result and calls
     payments.services.record_payment_result() exactly like the
     simulate view does now.
"""
import secrets
import string

RECEIPT_CHARS = string.ascii_uppercase + string.digits


def initiate_stk_push(*, phone, amount, order_number):
    """Pretend to send a prompt to the phone. Returns a fake request id."""
    return "SIM-" + secrets.token_hex(8)


def simulated_receipt():
    """An M-Pesa style receipt number, marked SIM so it can't be mistaken."""
    return "SIM" + "".join(secrets.choice(RECEIPT_CHARS) for _ in range(7))
