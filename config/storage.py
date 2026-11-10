from django.core.files.storage import FileSystemStorage, storages
from django.urls import reverse


class PrivateFileSystemStorage(FileSystemStorage):
    """Storage for files that must never be served from a public folder.

    Its links point at a view that checks who is asking.
    """

    def url(self, name):
        return reverse("private_file", kwargs={"path": name})


def private_storage():
    """Used by model fields, so migrations don't depend on the storage's settings."""
    return storages["private"]
