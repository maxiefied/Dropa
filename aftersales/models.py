from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Rating(models.Model):
    """One rating per delivered order: one for the shop, one for the rider."""

    order = models.OneToOneField(
        "orders.Order", on_delete=models.PROTECT, related_name="rating"
    )
    vendor = models.ForeignKey(
        "marketplace.Vendor", on_delete=models.PROTECT, related_name="ratings"
    )
    vendor_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    vendor_comment = models.CharField(max_length=300, blank=True)
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rider_ratings",
    )
    rider_rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    rider_comment = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order}: shop {self.vendor_rating}, rider {self.rider_rating}"


class Complaint(models.Model):
    class Reason(models.TextChoices):
        MISSING_ITEM = "missing_item", "Missing item"
        WRONG_ITEM = "wrong_item", "Wrong item"
        QUALITY = "quality", "Cold, spoiled or poor quality food"
        NOT_ARRIVED = "not_arrived", "Late or never arrived"
        RIDER = "rider", "Problem with the rider"
        OTHER = "other", "Something else"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        REFUNDED = "refunded", "Resolved with a refund"
        DISMISSED = "dismissed", "Resolved without a refund"

    order = models.OneToOneField(
        "orders.Order", on_delete=models.PROTECT, related_name="complaint"
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    description = models.TextField(max_length=1000)
    photo = models.ImageField(upload_to="complaint_photos/", blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN
    )

    vendor_response = models.TextField(max_length=1000, blank=True)
    vendor_responded_at = models.DateTimeField(null=True, blank=True)
    rider_response = models.TextField(max_length=1000, blank=True)
    rider_responded_at = models.DateTimeField(null=True, blank=True)

    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    resolution_note = models.CharField(
        max_length=300,
        blank=True,
        help_text="Shown to the customer when you resolve the complaint.",
    )
    refund_recorded = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Complaint on {self.order} ({self.get_status_display()})"

    def clean(self):
        if self.status == self.Status.REFUNDED:
            if not self.refund_amount or self.refund_amount <= 0:
                raise ValidationError({"refund_amount": "Enter the refund amount."})
            if self.refund_amount > self.order.total:
                raise ValidationError(
                    {
                        "refund_amount": (
                            "A refund can't be more than the order total "
                            f"(KSh {self.order.total})."
                        )
                    }
                )
        elif self.refund_amount:
            raise ValidationError(
                {"refund_amount": "Only set a refund amount when resolving with a refund."}
            )
