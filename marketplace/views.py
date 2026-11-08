from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.decorators import role_required
from accounts.models import User

from .forms import DocumentForm, MenuItemForm, ShopForm
from .models import MenuItem, Vendor

vendor_only = role_required(User.Role.VENDOR)
customer_only = role_required(User.Role.CUSTOMER, User.Role.ADMIN)


def get_vendor(user):
    return Vendor.objects.filter(owner=user).first()


# ----- Vendor side -----


@vendor_only
def vendor_home(request):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    return render(
        request,
        "marketplace/vendor_home.html",
        {
            "vendor": vendor,
            "documents": vendor.documents.all(),
            "doc_form": DocumentForm(),
            "menu_items": vendor.menu_items.all(),
        },
    )


@vendor_only
def shop_edit(request):
    vendor = get_vendor(request.user)

    if request.method == "POST":
        form = ShopForm(request.POST, instance=vendor)
        if form.is_valid():
            shop = form.save(commit=False)
            shop.owner = request.user
            shop.save()
            messages.success(request, "Shop details saved.")
            return redirect("marketplace:vendor_home")
    else:
        form = ShopForm(instance=vendor)

    back_url = (
        reverse("marketplace:vendor_home")
        if vendor
        else reverse("accounts:dashboard")
    )
    return render(
        request,
        "marketplace/form.html",
        {
            "form": form,
            "title": "Set up your shop" if vendor is None else "Edit shop details",
            "submit_label": "Save shop",
            "back_url": back_url,
        },
    )


@vendor_only
@require_POST
def document_upload(request):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")

    form = DocumentForm(request.POST, request.FILES)
    if form.is_valid():
        document = form.save(commit=False)
        document.vendor = vendor
        document.save()
        messages.success(request, "Document uploaded. We'll review it soon.")
    else:
        messages.error(request, "Choose a document type and a file, then try again.")
    return redirect("marketplace:vendor_home")


@vendor_only
@require_POST
def toggle_open(request):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")

    if not vendor.is_verified:
        messages.error(request, "You can go online once your shop is verified.")
    else:
        vendor.is_open = not vendor.is_open
        vendor.save(update_fields=["is_open"])
    return redirect("marketplace:vendor_home")


@vendor_only
def menu_item_create(request):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.vendor = vendor
            item.save()
            messages.success(request, f"{item.name} added to your menu.")
            return redirect("marketplace:vendor_home")
    else:
        form = MenuItemForm()

    return render(
        request,
        "marketplace/form.html",
        {
            "form": form,
            "title": "Add a menu item",
            "submit_label": "Add item",
            "back_url": reverse("marketplace:vendor_home"),
        },
    )


@vendor_only
def menu_item_edit(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    item = get_object_or_404(MenuItem, pk=pk, vendor=vendor)

    if request.method == "POST":
        form = MenuItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"{item.name} updated.")
            return redirect("marketplace:vendor_home")
    else:
        form = MenuItemForm(instance=item)

    return render(
        request,
        "marketplace/form.html",
        {
            "form": form,
            "title": f"Edit {item.name}",
            "submit_label": "Save changes",
            "back_url": reverse("marketplace:vendor_home"),
        },
    )


@vendor_only
@require_POST
def menu_item_toggle(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    item = get_object_or_404(MenuItem, pk=pk, vendor=vendor)
    item.is_available = not item.is_available
    item.save(update_fields=["is_available"])
    return redirect("marketplace:vendor_home")


@vendor_only
@require_POST
def menu_item_delete(request, pk):
    vendor = get_vendor(request.user)
    if vendor is None:
        return redirect("marketplace:shop_edit")
    item = get_object_or_404(MenuItem, pk=pk, vendor=vendor)
    name = item.name
    item.delete()
    messages.success(request, f"{name} removed from your menu.")
    return redirect("marketplace:vendor_home")


# ----- Customer side (browsing only for now) -----


@customer_only
def shop_list(request):
    vendors = Vendor.objects.filter(status=Vendor.Status.APPROVED).select_related(
        "block"
    )
    return render(request, "marketplace/shop_list.html", {"vendors": vendors})


@customer_only
def shop_detail(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk, status=Vendor.Status.APPROVED)
    return render(
        request,
        "marketplace/shop_detail.html",
        {"vendor": vendor, "menu_items": vendor.menu_items.all()},
    )
