from django import forms

from marketplace.forms import style_fields

from .models import Rider, RiderDocument


class RiderPhotoForm(forms.ModelForm):
    class Meta:
        model = Rider
        fields = ["photo"]
        labels = {"photo": "Your photo"}
        help_texts = {
            "photo": "A clear photo of your face. It goes on your name tag, and people use it to check it's you."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)


class RiderDocumentForm(forms.ModelForm):
    class Meta:
        model = RiderDocument
        fields = ["doc_type", "file"]
        labels = {"doc_type": "Document type", "file": "File"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self)
