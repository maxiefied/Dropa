from django.conf import settings
from django.db import models


class Payment(models.Model):
    """One M-Pesa prompt sent to a phone for an order."""

    class Status(models.TextChoices):
        PENDING = "pending", "Waiting for PIN"
        SUCCESS = "success", "Paid"
        FAILED = "failed", "Failed"
        LATE = "late", "Paid too late, refund due"

    order = models.ForeignKey(
        "orders.Order", on_delete=models.PROTECT, related_name="payments"
    )
    phone = models.CharField(max_length=12)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    checkout_request_id = models.CharField(max_length=64, unique=True)
    receipt_number = models.CharField(max_length=20, blank=True)
    result_description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order} {self.get_status_display()} ({self.phone})"

    @property
    def phone_display(self):
        if self.phone.startswith("254"):
            return "0" + self.phone[3:]
        return self.phone


class LedgerEntry(models.Model):
    """Append-only record of money moving. Rows are never edited or deleted."""

    class Kind(models.TextChoices):
        PAYMENT_RECEIVED = "payment_received", "Payment received"
        REFUND_DUE = "refund_due", "Refund due to customer"
        VENDOR_PAYOUT = "vendor_payout", "Vendor payout"  # later stage
        RIDER_EARNING = "rider_earning", "Rider earning"  # later stage

    order = models.ForeignKey(
        "orders.Order",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    payment = models.ForeignKey(
        Payment, null=True, blank=True, on_delete=models.PROTECT
    )
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name_plural = "ledger entries"

    def __str__(self):
        return f"{self.get_kind_display()}: KSh {self.amount}"
