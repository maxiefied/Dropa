from django import template

register = template.Library()

STEPS = [
    ("placed", "Placed"),
    ("accepted", "Accepted"),
    ("paid", "Paid"),
    ("picked", "On the way"),
    ("delivered", "Delivered"),
]


@register.simple_tag
def order_steps(order):
    """Steps for the progress tracker. Orders that ended early (rejected,
    expired, cancelled) get no tracker, since they have their own message."""
    keys = [key for key, _ in STEPS]
    if order.status not in keys:
        return []

    current = keys.index(order.status)
    steps = []
    for index, (key, label) in enumerate(STEPS):
        if order.status == "delivered" or index < current:
            state = "done"
        elif index == current:
            state = "current"
        else:
            state = "todo"
        steps.append({"label": label, "state": state})
    return steps
