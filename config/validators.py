from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

MAX_UPLOAD_MB = 5

# Documents may be photos or PDFs. Anything else (HTML, SVG, scripts) is refused.
validate_document_extension = FileExtensionValidator(
    ["pdf", "jpg", "jpeg", "png", "webp"]
)


def validate_file_size(file):
    if file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValidationError(f"Files can be at most {MAX_UPLOAD_MB} MB.")
