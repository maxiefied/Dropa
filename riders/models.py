import uuid

from django.conf import settings
from django.db import models


class Rider(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Verified"
        REJECTED = "rejected", "Not approved"
        SUSPENDED = "suspended", "Suspended"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="rider_profile",
    )
    photo = models.ImageField(upload_to="rider_photos/")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    rejection_reason = models.CharField(max_length=300, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    # The name tag's QR code points at a page keyed by this token. Issuing a
    # new token makes any old printed tag stop working.
    tag_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.name} ({self.get_status_display()})"

    @property
    def is_verified(self):
        return self.status == self.Status.APPROVED


class RiderDocument(models.Model):
    class DocType(models.TextChoices):
        NATIONAL_ID = "national_id", "National ID (front and back)"
        OTHER = "other", "Other"

    rider = models.ForeignKey(
        Rider, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file = models.FileField(upload_to="rider_documents/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.rider.user.name} - {self.get_doc_type_display()}"
