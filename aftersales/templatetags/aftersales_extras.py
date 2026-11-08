from django import template
from django.db.models import Avg, Count

from orders.models import Order

from ..models import Rating
from ..services import complaint_block_reason

register = template.Library()

# Averages are hidden until there are enough ratings to mean something.
MIN_RATINGS_TO_SHOW = 3


def summarize(queryset, field):
    data = queryset.aggregate(average=Avg(field), count=Count(field))
    count = data["count"]
    average = round(data["average"], 1) if data["average"] is not None else None
    return {"average": average, "count": count, "show": count >= MIN_RATINGS_TO_SHOW}


@register.simple_tag
def vendor_rating(vendor):
    return summarize(Rating.objects.filter(vendor=vendor), "vendor_rating")


@register.simple_tag
def rider_rating(user):
    return summarize(Rating.objects.filter(rider=user), "rider_rating")


@register.simple_tag
def order_extras(order):
    """What the customer can do next with this order, for its detail page."""
    rating = getattr(order, "rating", None)
    complaint = getattr(order, "complaint", None)
    return {
        "can_receipt": order.paid_at is not None,
        "can_rate": order.status == Order.Status.DELIVERED and rating is None,
        "can_complain": complaint is None and complaint_block_reason(order) is None,
        "rating": rating,
        "complaint": complaint,
    }
