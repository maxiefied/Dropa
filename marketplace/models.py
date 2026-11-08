from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Zone(models.Model):
    """An area Dropa serves. Fees live here so each zone can have its own."""

    name = models.CharField(max_length=100, unique=True)
    flat_delivery_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("100"),
        help_text="What the customer pays for delivery, in KSh.",
    )
    rider_share_percent = models.PositiveSmallIntegerField(
        default=80,
        validators=[MaxValueValidator(100)],
        help_text="Percent of the delivery fee the rider earns.",
    )
    service_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("20"),
        help_text="Dropa's service fee per order, in KSh.",
    )
    vendor_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="Percent of the goods total that Dropa keeps from the vendor.",
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Block(models.Model):
    """A block or building in a zone. This feeds the address dropdown."""

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="blocks")
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["zone", "name"], name="unique_block_per_zone"
            )
        ]

    def __str__(self):
        return self.name


class Vendor(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Verified"
        REJECTED = "rejected", "Not approved"
        SUSPENDED = "suspended", "Suspended"

    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vendor"
    )
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    block = models.ForeignKey(
        Block, on_delete=models.PROTECT, related_name="vendors"
    )
    location_note = models.CharField(max_length=200, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    rejection_reason = models.CharField(max_length=300, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_open = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def zone(self):
        return self.block.zone

    @property
    def is_verified(self):
        return self.status == self.Status.APPROVED


class VendorDocument(models.Model):
    class DocType(models.TextChoices):
        OWNER_ID = "owner_id", "Owner's national ID"
        BUSINESS_PERMIT = "business_permit", "Business permit"
        FOOD_SAFETY = "food_safety", "Food safety or health certificate"
        OTHER = "other", "Other"

    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file = models.FileField(upload_to="vendor_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.vendor} - {self.get_doc_type_display()}"


class MenuItem(models.Model):
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="menu_items"
    )
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True)
    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("1"))],
        help_text="In KSh.",
    )
    photo = models.ImageField(upload_to="menu_photos/", blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.vendor})"
