from django.urls import path

from . import views

app_name = "payouts"

urlpatterns = [
    path("rider/earnings/", views.rider_earnings, name="rider_earnings"),
    path("vendor/payouts/", views.vendor_payouts, name="vendor_payouts"),
]
