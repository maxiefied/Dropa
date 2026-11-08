from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    # Customers
    path("orders/", views.order_list, name="order_list"),
    path("orders/start/", views.checkout_start, name="checkout_start"),
    path("orders/checkout/", views.checkout, name="checkout"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/cancel/", views.order_cancel, name="order_cancel"),
    # Vendors
    path("vendor/orders/", views.vendor_orders, name="vendor_orders"),
    path("vendor/orders/<int:pk>/", views.vendor_order_detail, name="vendor_order_detail"),
    path("vendor/orders/<int:pk>/accept/", views.order_accept, name="order_accept"),
    path("vendor/orders/<int:pk>/reject/", views.order_reject, name="order_reject"),
    path("vendor/orders/<int:pk>/ready/", views.order_ready, name="order_ready"),
]
