from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("", views.register, name="register"),
    path("records/", views.record_list, name="record_list"),
]
