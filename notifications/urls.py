from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path(
        "students/<int:student_pk>/clear/",
        views.clear_student_emails,
        name="clear_student_emails",
    ),
]
