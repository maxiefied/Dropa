import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

ORDER_NUMBER_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I


class InvalidTransition(Exception):
    """Raised when an order can't move to the requested status."""


def payment_window_minutes():
    return getattr(settings, "DROPA_PAYMENT_WINDOW_MINUTES", 10)


def vendor_response_minutes():
    return getattr(settings, "DROPA_VENDOR_RESPONSE_MINUTES", 5)


def generate_order_number():
    while True:
        number = "DR-" + "".join(
            secrets.choice(ORDER_NUMBER_ALPHABET) for _ in range(6)
        )
        if not Order.objects.filter(order_number=number).exists():
            return number


class SavedAddress(models.Model):
    """One saved location per customer, used to prefill checkout."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_address",
    )
    block = models.ForeignKey(
        "marketplace.Block", null=True, blank=True, on_delete=models.SET_NULL
    )
    other_text = models.CharField(max_length=100, blank=True)
    floor = models.CharField(max_length=10)
    room = models.CharField(max_length=20)

    def __str__(self):
        return f"Saved address of {self.user}"


class Order(models.Model):
    class Status(models.TextChoices):
        PLACED = "placed", "Placed"
        ACCEPTED = "accepted", "Accepted"
        PAID = "paid", "Paid"
        PICKED = "picked", "Picked up"
        DELIVERED = "delivered", "Delivered"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        CANCELLED = "cancelled", "Cancelled"

    # Which status can follow which. "Claimed" and "ready" are not statuses:
    # they are the rider field and ready_at (used in later stages).
    ALLOWED_TRANSITIONS = {
        Status.PLACED: {
            Status.ACCEPTED,
            Status.REJECTED,
            Status.CANCELLED,
            Status.EXPIRED,
        },
        Status.ACCEPTED: {Status.PAID, Status.CANCELLED, Status.EXPIRED},
        Status.PAID: {Status.PICKED},
        Status.PICKED: {Status.DELIVERED},
    }

    order_number = models.CharField(max_length=12, unique=True, editable=False)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    vendor = models.ForeignKey(
        "marketplace.Vendor", on_delete=models.PROTECT, related_name="orders"
    )
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLACED
    )

    # Address snapshot: copied at order time so later edits can't change it.
    address_block = models.CharField(max_length=100)
    address_is_other = models.BooleanField(default=False)
    address_floor = models.CharField(max_length=10)
    address_room = models.CharField(max_length=20)
    rider_note = models.CharField(max_length=200, blank=True)

    # Handover: the customer reads this code to the rider at the door.
    delivery_code = models.CharField(max_length=4, blank=True)
    delivery_code_attempts = models.PositiveSmallIntegerField(default=0)

    # Money, calculated once when the order is placed.
    goods_total = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    rider_earnings = models.DecimalField(max_digits=10, decimal_places=2)
    vendor_payout = models.DecimalField(max_digits=10, decimal_places=2)

    # Deadlines and stage timestamps.
    vendor_response_deadline = models.DateTimeField(null=True, blank=True)
    payment_deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)  # later stage
    ready_at = models.DateTimeField(null=True, blank=True)
    picked_at = models.DateTimeField(null=True, blank=True)  # later stage
    delivered_at = models.DateTimeField(null=True, blank=True)  # later stage

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = generate_order_number()
        super().save(*args, **kwargs)

    # ----- display helpers -----

    @property
    def address_display(self):
        return f"{self.address_block}, floor {self.address_floor}, room {self.address_room}"

    @property
    def customer_status_text(self):
        return {
            self.Status.PLACED: "Waiting for the shop to accept",
            self.Status.ACCEPTED: "Accepted, waiting for your payment",
            self.Status.PAID: "Paid, the shop is preparing your order",
            self.Status.PICKED: "On its way to you",
            self.Status.DELIVERED: "Delivered",
            self.Status.REJECTED: "The shop couldn't take this order",
            self.Status.EXPIRED: "Expired",
            self.Status.CANCELLED: "Cancelled",
        }.get(self.status, self.get_status_display())

    @property
    def badge_class(self):
        return {
            self.Status.PLACED: "text-bg-warning",
            self.Status.ACCEPTED: "text-bg-info",
            self.Status.PAID: "text-bg-primary",
            self.Status.PICKED: "text-bg-primary",
            self.Status.DELIVERED: "text-bg-success",
            self.Status.REJECTED: "text-bg-secondary",
            self.Status.EXPIRED: "text-bg-secondary",
            self.Status.CANCELLED: "text-bg-secondary",
        }.get(self.status, "text-bg-light")

    @property
    def is_active(self):
        return self.status in {
            self.Status.PLACED,
            self.Status.ACCEPTED,
            self.Status.PAID,
            self.Status.PICKED,
        }

    # ----- status changes -----

    @transaction.atomic
    def move_to(self, new_status, by=None, note=""):
        """Change status safely, stamp the time, and write the history row."""
        allowed = self.ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidTransition(
                f"An order that is '{self.status}' can't become '{new_status}'."
            )

        now = timezone.now()
        fields = {"status": new_status}
        if new_status == self.Status.ACCEPTED:
            fields["accepted_at"] = now
            fields["payment_deadline"] = now + timedelta(
                minutes=payment_window_minutes()
            )
        elif new_status == self.Status.PAID:
            fields["paid_at"] = now
            fields["delivery_code"] = f"{secrets.randbelow(10000):04d}"
        elif new_status == self.Status.PICKED:
            fields["picked_at"] = now
        elif new_status == self.Status.DELIVERED:
            fields["delivered_at"] = now

        # Only update if nobody changed the order since we loaded it.
        updated = Order.objects.filter(pk=self.pk, status=self.status).update(
            **fields
        )
        if not updated:
            raise InvalidTransition("This order was just updated. Please refresh.")

        for name, value in fields.items():
            setattr(self, name, value)
        OrderStatusHistory.objects.create(
            order=self, status=new_status, changed_by=by, note=note
        )

    @transaction.atomic
    def mark_ready(self, by=None):
        """The vendor says the food is ready. Only possible once paid."""
        if self.status != self.Status.PAID or self.ready_at is not None:
            raise InvalidTransition("This order can't be marked ready.")
        now = timezone.now()
        updated = Order.objects.filter(
            pk=self.pk, status=self.Status.PAID, ready_at__isnull=True
        ).update(ready_at=now)
        if not updated:
            raise InvalidTransition("This order was just updated. Please refresh.")
        self.ready_at = now
        OrderStatusHistory.objects.create(
            order=self, status=self.status, changed_by=by, note="Marked ready"
        )


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(
        "marketplace.MenuItem", null=True, on_delete=models.SET_NULL
    )
    # Copied from the menu so later menu edits don't change old orders.
    name = models.CharField(max_length=120)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveSmallIntegerField()

    @property
    def line_total(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.name}"


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="history"
    )
    status = models.CharField(max_length=10, choices=Order.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name_plural = "order status history"

    def __str__(self):
        return f"{self.order} -> {self.status}"
