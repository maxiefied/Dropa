from django import forms

from accounts.utils import normalize_phone
from marketplace.forms import style_fields


class PayForm(forms.Form):
    phone = forms.CharField(
        label="M-Pesa phone number",
        widget=forms.TextInput(
            attrs={"inputmode": "tel", "placeholder": "0712345678"}
        ),
        help_text="You can use any M-Pesa number, such as a family member's.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_phone(self):
        try:
            return normalize_phone(self.cleaned_data["phone"])
        except ValueError as error:
            raise forms.ValidationError(str(error))
