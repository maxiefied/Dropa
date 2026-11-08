from django import forms

from .models import Block, MenuItem, Vendor, VendorDocument


def style_fields(form):
    """Give every field the Bootstrap look."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            css = "form-check-input"
        elif isinstance(widget, forms.Select):
            css = "form-select"
        else:
            css = "form-control"
        widget.attrs.setdefault("class", css)


class ShopForm(forms.ModelForm):
    class Meta:
        model = Vendor
        fields = ["name", "description", "block", "location_note"]
        labels = {
            "name": "Shop name",
            "description": "Short description",
            "block": "Where is your shop?",
            "location_note": "Extra directions",
        }
        help_texts = {
            "location_note": "For example: ground floor, shop 3.",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["block"].queryset = Block.objects.filter(
            is_active=True, zone__is_active=True
        )
        self.fields["block"].empty_label = "Select a block"
        style_fields(self)


class DocumentForm(forms.ModelForm):
    class Meta:
        model = VendorDocument
        fields = ["doc_type", "file"]
        labels = {"doc_type": "Document type", "file": "File"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = ["name", "description", "price", "photo", "is_available"]
        labels = {
            "name": "Item name",
            "description": "Description",
            "price": "Price (KSh)",
            "photo": "Photo",
            "is_available": "Available to order",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
