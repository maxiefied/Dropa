from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from payments.models import LedgerEntry


class Payout(models.Model):
    """One M-Pesa transfer from Dropa to a vendor, a rider, or a customer."""

    class Kind(models.TextChoices):
        VENDOR = "vendor", "Vendor payout"
        RIDER = "rider", "Rider payout"
        REFUND = "refund", "Customer refund"

    class Status(models.TextChoices):
        PENDING = "pending", "Not sent yet"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    kind = models.CharField(max_length=10, choices=Kind.choices)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payouts"
    )
    phone = models.CharField(max_length=12)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    reference = models.CharField(max_length=40, blank=True)
    failure_reason = models.CharField(max_length=200, blank=True)
    note = models.CharField(max_length=200, blank=True)
    period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.get_kind_display()} KSh {self.amount} to {self.phone} ({self.get_status_display()})"

    @property
    def phone_display(self):
        if self.phone.startswith("254"):
            return "0" + self.phone[3:]
        return self.phone


class PayoutLine(models.Model):
    """Links a ledger entry to the payout that settled it.

    The ledger itself is never edited. Because each ledger entry can appear in
    only one payout line, an entry can never be paid twice.
    """

    payout = models.ForeignKey(Payout, on_delete=models.CASCADE, related_name="lines")
    ledger_entry = models.OneToOneField(
        LedgerEntry, on_delete=models.PROTECT, related_name="payout_line"
    )

    def __str__(self):
        return f"{self.payout_id}: {self.ledger_entry}"


class RiderDeduction(models.Model):
    """Money taken off a rider's next payout, for example after an upheld complaint."""

    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="deductions",
        limit_choices_to={"role": "rider"},
    )
    order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.PROTECT
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    reason = models.CharField(max_length=200)
    ledger_entry = models.OneToOneField(
        LedgerEntry,
        null=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Deduction of KSh {self.amount} from {self.rider}"
