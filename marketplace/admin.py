from django.contrib import admin
from django.utils import timezone

from .models import Block, MenuItem, Vendor, VendorDocument, Zone


class BlockInline(admin.TabularInline):
    model = Block
    extra = 3


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "flat_delivery_fee",
        "rider_share_percent",
        "service_fee",
        "vendor_commission_percent",
        "is_active",
    )
    inlines = [BlockInline]


class VendorDocumentInline(admin.TabularInline):
    model = VendorDocument
    extra = 0
    readonly_fields = ("uploaded_at",)


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0
    fields = ("name", "price", "is_available")


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "block", "status", "is_open", "verified_at")
    list_filter = ("status", "is_open")
    search_fields = ("name", "owner__phone", "owner__name")
    readonly_fields = ("verified_at", "created_at")
    inlines = [VendorDocumentInline, MenuItemInline]
    actions = ["approve_vendors", "reject_vendors", "suspend_vendors"]

    def save_model(self, request, obj, form, change):
        if obj.status == Vendor.Status.APPROVED:
            if obj.verified_at is None:
                obj.verified_at = timezone.now()
        else:
            obj.verified_at = None
            obj.is_open = False
        super().save_model(request, obj, form, change)

    @admin.action(description="Verify selected shops")
    def approve_vendors(self, request, queryset):
        count = queryset.update(
            status=Vendor.Status.APPROVED,
            verified_at=timezone.now(),
            rejection_reason="",
        )
        self.message_user(request, f"{count} shop(s) verified.")

    @admin.action(description="Reject selected shops (add a reason on each shop)")
    def reject_vendors(self, request, queryset):
        count = queryset.update(
            status=Vendor.Status.REJECTED, verified_at=None, is_open=False
        )
        self.message_user(request, f"{count} shop(s) rejected.")

    @admin.action(description="Suspend selected shops")
    def suspend_vendors(self, request, queryset):
        count = queryset.update(
            status=Vendor.Status.SUSPENDED, verified_at=None, is_open=False
        )
        self.message_user(request, f"{count} shop(s) suspended.")
