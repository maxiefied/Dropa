from django import forms

from marketplace.forms import style_fields

from .models import Complaint

STAR_CHOICES = [(value, str(value)) for value in range(1, 6)]


def star_field(label):
    return forms.TypedChoiceField(
        label=label,
        choices=STAR_CHOICES,
        coerce=int,
        widget=forms.RadioSelect(attrs={"class": "btn-check"}),
    )


def comment_field():
    return forms.CharField(
        label="Comment (optional)",
        required=False,
        max_length=300,
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )


class RatingForm(forms.Form):
    vendor_rating = star_field("How were the food and the shop?")
    vendor_comment = comment_field()
    rider_rating = star_field("How was the rider?")
    rider_comment = comment_field()


class ComplaintForm(forms.ModelForm):
    description = forms.CharField(
        label="What went wrong?",
        min_length=10,
        max_length=1000,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="Give enough detail for us to look into it.",
    )

    class Meta:
        model = Complaint
        fields = ["reason", "description", "photo"]
        labels = {"reason": "What kind of problem?", "photo": "Photo (optional)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
