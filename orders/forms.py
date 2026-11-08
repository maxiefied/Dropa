from django import forms

from marketplace.forms import style_fields
from marketplace.models import Block


class CheckoutForm(forms.Form):
    block = forms.ModelChoiceField(
        queryset=Block.objects.none(),
        required=False,
        empty_label="Other (my block isn't listed)",
        label="Block",
    )
    other_location = forms.CharField(
        required=False,
        max_length=100,
        label="Your location",
        help_text="Type the block or building name.",
    )
    other_confirm = forms.BooleanField(required=False, label="This location is inside the estate")
    floor = forms.CharField(max_length=10, label="Floor")
    room = forms.CharField(max_length=20, label="Room or house number")
    rider_note = forms.CharField(
        required=False,
        max_length=200,
        label="Note for the rider",
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="For example: call when you reach the gate. The shop can't see this.",
    )
    save_address = forms.BooleanField(
        required=False, label="Save this location for next time"
    )

    def __init__(self, *args, zone, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["block"].queryset = Block.objects.filter(zone=zone, is_active=True)
        self.fields["other_confirm"].label = f"This location is inside {zone.name}"
        style_fields(self)

    def clean(self):
        cleaned = super().clean()
        block = cleaned.get("block")
        other = (cleaned.get("other_location") or "").strip()

        if not block:
            if not other:
                self.add_error(
                    "other_location",
                    "Pick your block, or choose Other and type your location.",
                )
            elif not cleaned.get("other_confirm"):
                self.add_error(
                    "other_confirm", "Please confirm this location is inside the estate."
                )
        return cleaned
