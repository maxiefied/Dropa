from django.urls import path

from . import views

app_name = "marketplace"

urlpatterns = [
    # Customers
    path("shops/", views.shop_list, name="shop_list"),
    path("shops/<int:pk>/", views.shop_detail, name="shop_detail"),
    # Vendors
    path("vendor/", views.vendor_home, name="vendor_home"),
    path("vendor/shop/", views.shop_edit, name="shop_edit"),
    path("vendor/documents/", views.document_upload, name="document_upload"),
    path("vendor/open-toggle/", views.toggle_open, name="toggle_open"),
    path("vendor/menu/new/", views.menu_item_create, name="menu_item_create"),
    path("vendor/menu/<int:pk>/edit/", views.menu_item_edit, name="menu_item_edit"),
    path("vendor/menu/<int:pk>/toggle/", views.menu_item_toggle, name="menu_item_toggle"),
    path("vendor/menu/<int:pk>/delete/", views.menu_item_delete, name="menu_item_delete"),
]
