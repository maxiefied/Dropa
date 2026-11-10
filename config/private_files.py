import mimetypes

from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation
from django.core.files.storage import FileSystemStorage, storages
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.views.decorators.cache import never_cache

from aftersales.models import Complaint
from marketplace.models import VendorDocument
from riders.models import RiderDocument

INLINE_TYPES = ("image/", "application/pdf")


def user_may_view(user, name):
    """True or False if the file is known, None if no record owns this file."""
    staff = user.is_staff or user.is_superuser

    document = VendorDocument.objects.filter(file=name).select_related("vendor").first()
    if document:
        return staff or document.vendor.owner_id == user.pk

    document = RiderDocument.objects.filter(file=name).select_related("rider").first()
    if document:
        return staff or document.rider.user_id == user.pk

    complaint = (
        Complaint.objects.filter(photo=name)
        .select_related("order__vendor")
        .first()
    )
    if complaint:
        order = complaint.order
        return staff or user.pk in (order.customer_id, order.vendor.owner_id, order.rider_id)

    return None


@login_required
@never_cache
def serve(request, path):
    # Same 404 whether the file doesn't exist or you may not see it,
    # so the page never confirms that a given file exists.
    if not user_may_view(request.user, path):
        raise Http404

    storage = storages["private"]
    if not isinstance(storage, FileSystemStorage):
        return redirect(storage.url(path))  # a short-lived signed link

    try:
        handle = storage.open(path, "rb")
    except (FileNotFoundError, SuspiciousOperation):
        raise Http404

    content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    inline = content_type.startswith(INLINE_TYPES)
    return FileResponse(handle, content_type=content_type, as_attachment=not inline)
