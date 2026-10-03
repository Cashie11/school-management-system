from django.urls import path

from . import views

app_name = "tenancy"

urlpatterns = [
    path("schools/", views.school_list, name="school_list"),
    path("schools/<int:pk>/open/", views.school_open, name="school_open"),
    path("schools/clear/", views.school_clear, name="school_clear"),
]
