from django.urls import path

from . import views

app_name = "riders"

urlpatterns = [
    path("rider/", views.rider_home, name="rider_home"),
    path("rider/profile/", views.profile_edit, name="profile_edit"),
    path("rider/documents/", views.document_upload, name="document_upload"),
    path("rider/tag/", views.name_tag, name="name_tag"),
    path("verify/<uuid:token>/", views.verify, name="verify"),
    path("rider/available/", views.available, name="available"),
    path("rider/available/<int:pk>/claim/", views.claim, name="claim"),
    path("rider/deliveries/", views.deliveries, name="deliveries"),
    path("rider/deliveries/<int:pk>/", views.delivery_detail, name="delivery_detail"),
    path("rider/deliveries/<int:pk>/picked/", views.picked, name="picked"),
    path("rider/deliveries/<int:pk>/deliver/", views.deliver, name="deliver"),
]
