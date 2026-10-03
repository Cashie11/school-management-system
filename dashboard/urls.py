from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("classes/", views.class_list, name="class_list"),
    path("classes/<int:pk>/", views.class_detail, name="class_detail"),
]
