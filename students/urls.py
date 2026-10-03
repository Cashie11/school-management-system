from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.student_list, name="student_list"),
    path("new/", views.student_create, name="student_create"),
    path("<int:pk>/", views.student_detail, name="student_detail"),
    path("<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("<int:pk>/delete/", views.student_delete, name="student_delete"),
    path("enrollments/", views.enrollment_list, name="enrollment_list"),
    path("enrollments/new/", views.enrollment_create, name="enrollment_create"),
    path("enrollments/<int:pk>/delete/", views.enrollment_delete, name="enrollment_delete"),
    path("guardians/", views.guardian_list, name="guardian_list"),
    path("guardians/new/", views.guardian_create, name="guardian_create"),
    path("guardians/<int:pk>/delete/", views.guardian_delete, name="guardian_delete"),
    path("discipline/", views.discipline_list, name="discipline_list"),
    path("discipline/new/", views.discipline_create, name="discipline_create"),
]
