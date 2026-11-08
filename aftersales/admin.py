from django.contrib import admin
from django.utils import timezone

from payments.models import LedgerEntry

from .models import Complaint, Rating


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("order", "vendor", "vendor_rating", "rider", "rider_rating", "created_at")
    list_filter = ("vendor_rating", "rider_rating", "vendor")
    search_fields = ("order__order_number", "vendor__name", "rider__name")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ("order", "reason", "status", "vendor_name", "rider_name", "refund_amount", "created_at")
    list_filter = ("status", "reason", "order__vendor")
    search_fields = ("order__order_number",)
    fieldsets = (
        ("Complaint", {"fields": ("order", "reason", "description", "photo", "created_at")}),
        ("Responses", {"fields": ("vendor_response", "vendor_responded_at", "rider_response", "rider_responded_at")}),
        ("Decision", {"fields": ("status", "refund_amount", "resolution_note", "resolved_at")}),
    )
    base_readonly = (
        "order",
        "reason",
        "description",
        "photo",
        "created_at",
        "vendor_response",
        "vendor_responded_at",
        "rider_response",
        "rider_responded_at",
        "resolved_at",
    )

    @admin.display(description="Shop")
    def vendor_name(self, obj):
        return obj.order.vendor.name

    @admin.display(description="Rider")
    def rider_name(self, obj):
        return obj.order.rider.name if obj.order.rider else "-"

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.base_readonly)
        # A resolved complaint is final, so the ledger never double-counts a refund.
        if obj and obj.status != Complaint.Status.OPEN:
            readonly += ["status", "refund_amount", "resolution_note"]
        return readonly

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if obj.status != Complaint.Status.OPEN and obj.resolved_at is None:
            obj.resolved_at = timezone.now()
        super().save_model(request, obj, form, change)

        if obj.status == Complaint.Status.REFUNDED and not obj.refund_recorded:
            LedgerEntry.objects.create(
                order=obj.order,
                kind=LedgerEntry.Kind.REFUND_DUE,
                amount=obj.refund_amount,
                note=f"Refund approved for complaint on {obj.order.order_number}",
            )
            Complaint.objects.filter(pk=obj.pk).update(refund_recorded=True)
