from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("orders/<int:pk>/pay/", views.pay, name="pay"),
    path("payments/<int:payment_id>/simulate/", views.simulate, name="simulate"),
]
