import uuid

from django.contrib import admin
from django.utils import timezone

from .models import Rider, RiderDocument


class RiderDocumentInline(admin.TabularInline):
    model = RiderDocument
    extra = 0
    readonly_fields = ("uploaded_at",)


@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "verified_at", "created_at")
    list_filter = ("status",)
    search_fields = ("user__name", "user__phone")
    readonly_fields = ("verified_at", "created_at", "tag_token")
    inlines = [RiderDocumentInline]
    actions = ["approve_riders", "reject_riders", "suspend_riders", "issue_new_tag"]

    def save_model(self, request, obj, form, change):
        if obj.status == Rider.Status.APPROVED:
            if obj.verified_at is None:
                obj.verified_at = timezone.now()
        else:
            obj.verified_at = None
        super().save_model(request, obj, form, change)

    @admin.action(description="Verify selected riders")
    def approve_riders(self, request, queryset):
        count = queryset.update(
            status=Rider.Status.APPROVED,
            verified_at=timezone.now(),
            rejection_reason="",
        )
        self.message_user(request, f"{count} rider(s) verified.")

    @admin.action(description="Reject selected riders (add a reason on each rider)")
    def reject_riders(self, request, queryset):
        count = queryset.update(status=Rider.Status.REJECTED, verified_at=None)
        self.message_user(request, f"{count} rider(s) rejected.")

    @admin.action(description="Suspend selected riders (their name tag stops verifying)")
    def suspend_riders(self, request, queryset):
        count = queryset.update(status=Rider.Status.SUSPENDED, verified_at=None)
        self.message_user(request, f"{count} rider(s) suspended.")

    @admin.action(description="Issue a new name tag (the old printed tag stops working)")
    def issue_new_tag(self, request, queryset):
        for rider in queryset:
            rider.tag_token = uuid.uuid4()
            rider.save(update_fields=["tag_token"])
        self.message_user(request, f"New tag issued for {queryset.count()} rider(s).")
