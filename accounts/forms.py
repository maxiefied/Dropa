from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User
from .utils import normalize_phone


def style_fields(form):
    """Give every field the Bootstrap look."""
    for field in form.fields.values():
        css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
        field.widget.attrs.setdefault("class", css)


class SignupForm(forms.ModelForm):
    password = forms.CharField(
        label="Password",
        min_length=6,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="At least 6 characters.",
    )
    role = forms.ChoiceField(
        label="I want to",
        choices=[
            (User.Role.CUSTOMER, "Order food"),
            (User.Role.VENDOR, "Sell food"),
            (User.Role.RIDER, "Deliver orders"),
        ],
    )

    class Meta:
        model = User
        fields = ["name", "phone"]
        labels = {"name": "Your name", "phone": "Phone number"}
        widgets = {
            "phone": forms.TextInput(
                attrs={"inputmode": "tel", "placeholder": "0712345678"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_phone(self):
        try:
            phone = normalize_phone(self.cleaned_data["phone"])
        except ValueError as error:
            raise forms.ValidationError(str(error))
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user


class PhoneLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Phone number",
        widget=forms.TextInput(
            attrs={"autofocus": True, "inputmode": "tel", "placeholder": "0712345678"}
        ),
    )
    error_messages = {
        "invalid_login": "Wrong phone number or password.",
        "inactive": "This account is switched off. Contact Dropa support.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)

    def clean_username(self):
        try:
            return normalize_phone(self.cleaned_data["username"])
        except ValueError as error:
            raise forms.ValidationError(str(error))
