from django.urls import path

from . import views

app_name = "aftersales"

urlpatterns = [
    path("orders/<int:pk>/rate/", views.rate, name="rate"),
    path("orders/<int:pk>/receipt/", views.receipt, name="receipt"),
    path("orders/<int:pk>/complain/", views.complain, name="complain"),
    path("vendor/orders/<int:pk>/complaint-response/", views.vendor_respond, name="vendor_respond"),
    path("rider/deliveries/<int:pk>/complaint-response/", views.rider_respond, name="rider_respond"),
]
