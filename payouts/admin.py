from django.contrib import admin

from payments.models import LedgerEntry

from .models import Payout, PayoutLine, RiderDeduction
from .services import send_payout


class PayoutLineInline(admin.TabularInline):
    model = PayoutLine
    extra = 0
    can_delete = False
    readonly_fields = ("ledger_entry",)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "recipient", "phone", "amount", "status", "reference")
    list_filter = ("kind", "status")
    search_fields = ("recipient__name", "recipient__phone", "reference")
    inlines = [PayoutLineInline]
    actions = ["retry_selected"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Retry sending selected failed payouts")
    def retry_selected(self, request, queryset):
        sent = 0
        for payout in queryset.filter(status=Payout.Status.FAILED):
            if send_payout(payout).status == Payout.Status.SENT:
                sent += 1
        self.message_user(request, f"{sent} payout(s) sent.")


@admin.register(RiderDeduction)
class RiderDeductionAdmin(admin.ModelAdmin):
    list_display = ("created_at", "rider", "amount", "order", "reason")
    search_fields = ("rider__name", "rider__phone", "reason")

    def get_readonly_fields(self, request, obj=None):
        if obj:  # once created, a deduction can't be edited
            return ["rider", "order", "amount", "reason", "created_at"]
        return []

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if change:
            return
        super().save_model(request, obj, form, change)
        entry = LedgerEntry.objects.create(
            order=obj.order,
            kind=LedgerEntry.Kind.RIDER_DEDUCTION,
            beneficiary=obj.rider,
            amount=obj.amount,
            note=f"Deduction: {obj.reason}"[:200],
        )
        RiderDeduction.objects.filter(pk=obj.pk).update(ledger_entry=entry)
