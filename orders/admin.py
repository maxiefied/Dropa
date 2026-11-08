from django.contrib import admin

from .models import Order, OrderItem, OrderStatusHistory, SavedAddress


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    fields = ("name", "unit_price", "quantity")
    readonly_fields = ("name", "unit_price", "quantity")

    def has_add_permission(self, request, obj=None):
        return False


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    can_delete = False
    fields = ("created_at", "status", "changed_by", "note")
    readonly_fields = ("created_at", "status", "changed_by", "note")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "vendor", "customer", "status", "total", "created_at")
    list_filter = ("status", "vendor")
    search_fields = ("order_number", "customer__phone", "customer__name", "vendor__name")
    inlines = [OrderItemInline, OrderStatusHistoryInline]

    def get_readonly_fields(self, request, obj=None):
        # Orders are created by the app and changed through its rules.
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False


admin.site.register(SavedAddress)
