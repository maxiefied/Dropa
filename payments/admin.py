from django.contrib import admin

from .models import LedgerEntry, Payment


class ReadOnlyAdmin(admin.ModelAdmin):
    """Money records are looked at, never edited by hand."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "order", "phone", "amount", "status", "receipt_number")
    list_filter = ("status",)
    search_fields = ("order__order_number", "phone", "receipt_number")


@admin.register(LedgerEntry)
class LedgerEntryAdmin(ReadOnlyAdmin):
    list_display = ("created_at", "kind", "amount", "order", "note")
    list_filter = ("kind",)
    search_fields = ("order__order_number", "note")
